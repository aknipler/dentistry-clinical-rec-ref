export default function ({ parentElement, data, setStateValue }) {
  // Persist connection objects on the DOM node itself: this function is
  // re-invoked on every Streamlit rerun, but `parentElement` (and anything
  // hung off it) survives across those calls, unlike locals in this scope.
  if (!parentElement.__realtimeVoice) {
    parentElement.__realtimeVoice = {
      pc: null,
      dc: null,
      micStream: null,
      messages: [],
      disconnectRequested: false,
    };
  }
  const rtc = parentElement.__realtimeVoice;

  const statusEl = parentElement.querySelector("#status");
  const transcriptEl = parentElement.querySelector("#transcript");
  const connectBtn = parentElement.querySelector("#connectBtn");
  const disconnectBtn = parentElement.querySelector("#disconnectBtn");
  const remoteAudio = parentElement.querySelector("#remoteAudio");

  transcriptEl.style.display = data && data.show_transcript ? "" : "none";
  
  function setStatus(text) {
    statusEl.textContent = text;
  }

  function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  function renderTranscript() {
    transcriptEl.innerHTML = rtc.messages
      .map(
        (m) =>
          "<p><b>" +
          (m.role === "user" ? "You" : "Patient") +
          ":</b> " +
          escapeHtml(m.content) +
          "</p>"
      )
      .join("");
    transcriptEl.scrollTop = transcriptEl.scrollHeight;
  }

  function pushMessage(role, content) {
    if (!content) return;
    rtc.messages.push({ role: role, content: content });
    renderTranscript();
    setStateValue("messages", rtc.messages.slice());
  }

  function handleServerEvent(event) {
    let payload;
    try {
      payload = JSON.parse(event.data);
    } catch (err) {
      return;
    }

    switch (payload.type) {
      case "conversation.item.input_audio_transcription.completed":
        pushMessage("user", payload.transcript || "");
        break;
      case "response.done": {
        const output = (payload.response && payload.response.output) || [];
        output.forEach((item) => {
          if (item.role !== "assistant" || !Array.isArray(item.content)) return;
          const text = item.content
            .map((part) => part.transcript || part.text || "")
            .join("")
            .trim();
          if (text) pushMessage("assistant", text);
        });
        break;
      }
      case "error":
        console.error("Realtime API error", payload);
        break;
      default:
        break;
    }
  }

  async function connect() {
    if (rtc.pc || !data || !data.client_secret) return;
    rtc.disconnectRequested = false;
    setStatus("Connecting...");
    connectBtn.disabled = true;

    const pc = new RTCPeerConnection();
    rtc.pc = pc;
    pc.ontrack = (event) => {
      remoteAudio.srcObject = event.streams[0];
    };

    try {
      rtc.micStream = await navigator.mediaDevices.getUserMedia({ 
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }, 
      });
    } catch (err) {
      setStatus("Microphone permission denied. Please allow microphone access and try again.");
      connectBtn.disabled = false;
      pc.close();
      rtc.pc = null;
      setStateValue("status", "mic_error");
      return;
    }
    rtc.micStream.getTracks().forEach((track) => pc.addTrack(track, rtc.micStream));

    const dc = pc.createDataChannel("oai-events");
    rtc.dc = dc;
    dc.addEventListener("message", handleServerEvent);

    try {
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      const sdpResponse = await fetch("https://api.openai.com/v1/realtime/calls", {
        method: "POST",
        body: offer.sdp,
        headers: {
          Authorization: "Bearer " + data.client_secret,
          "Content-Type": "application/sdp",
        },
      });

      if (!sdpResponse.ok) {
        throw new Error("OpenAI Realtime API returned " + sdpResponse.status);
      }

      const answerSdp = await sdpResponse.text();
      await pc.setRemoteDescription({ type: "answer", sdp: answerSdp });
    } catch (err) {
      setStatus("Failed to connect to OpenAI Realtime API: " + err.message);
      connectBtn.disabled = false;
      disconnect(true);
      setStateValue("status", "error");
      return;
    }

    setStatus("Connected \u2014 you can start talking.");
    disconnectBtn.disabled = false;
    setStateValue("status", "connected");
  }

  function disconnect(skipReport) {
    if (rtc.dc) {
      try {
        rtc.dc.close();
      } catch (err) {
        /* ignore */
      }
      rtc.dc = null;
    }
    if (rtc.pc) {
      try {
        rtc.pc.close();
      } catch (err) {
        /* ignore */
      }
      rtc.pc = null;
    }
    if (rtc.micStream) {
      rtc.micStream.getTracks().forEach((track) => track.stop());
      rtc.micStream = null;
    }
    connectBtn.disabled = false;
    disconnectBtn.disabled = true;
    if (!skipReport) {
      setStatus("Disconnected.");
      setStateValue("status", "disconnected");
    }
  }

  connectBtn.onclick = connect;
  disconnectBtn.onclick = () => disconnect(false);

  if (data && data.should_disconnect && rtc.pc && !rtc.disconnectRequested) {
    rtc.disconnectRequested = true;
    disconnect(false);
  }

  return () => {
    /* Intentionally no-op: the WebRTC connection must survive Streamlit reruns. */
  };
}
