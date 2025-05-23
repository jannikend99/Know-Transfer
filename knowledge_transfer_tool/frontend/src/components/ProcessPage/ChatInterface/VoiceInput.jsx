import React, { useState, useRef } from 'react';
import { Mic, MicOff } from 'lucide-react';
import { Button } from "../../ui/button";

const VoiceInput = ({ onSendVoice, disabled }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const handleStartRecording = async () => {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorderRef.current = new MediaRecorder(stream);
        audioChunksRef.current = [];

        mediaRecorderRef.current.ondataavailable = (event) => {
          audioChunksRef.current.push(event.data);
        };

        mediaRecorderRef.current.onstop = () => {
          const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          setAudioBlob(blob);
          console.log('Recorded audio blob:', blob);
          if (onSendVoice) {
             onSendVoice({ type: 'voice', content: blob });
          } else {
             alert('Voice recorded (simulated). Check console.');
          }
          // Reset for next recording
          audioChunksRef.current = [];
          // Stop tracks to release microphone
          stream.getTracks().forEach(track => track.stop());
        };

        mediaRecorderRef.current.start();
        setIsRecording(true);
        setAudioBlob(null);
      } catch (err) {
        console.error('Error accessing microphone:', err);
        alert('Error accessing microphone. Please check permissions.');
      }
    } else {
      alert('Audio recording is not supported in this browser.');
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  return (
    <Button
      variant={isRecording ? "destructive" : "outline"}
      size="sm"
      onClick={isRecording ? handleStopRecording : handleStartRecording}
      disabled={disabled}
      className="flex items-center space-x-2"
    >
      {isRecording ? (
        <>
          <MicOff className="h-4 w-4" />
          <span>Stop Recording</span>
        </>
      ) : (
        <>
          <Mic className="h-4 w-4" />
          <span>Voice</span>
        </>
      )}
    </Button>
  );
};

export default VoiceInput; 