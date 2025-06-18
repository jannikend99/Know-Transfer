import React, { useState, useRef, useEffect } from 'react';
import { Mic, MicOff, AlertCircle } from 'lucide-react';
import { Button } from "../../ui/button";

const VoiceInput = ({ onSendVoice, onRecordingStateChange, disabled }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [isSupported, setIsSupported] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  useEffect(() => {
    // Check if audio recording is supported
    const checkSupport = () => {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setIsSupported(false);
        setErrorMessage('Audio recording is not supported in this browser.');
        return;
      }

      // Check if we're in a secure context (HTTPS or localhost)
      if (!window.isSecureContext && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
        setIsSupported(false);
        setErrorMessage('Audio recording requires HTTPS. Please access the site via HTTPS or localhost.');
        return;
      }

      setIsSupported(true);
      setErrorMessage('');
    };

    checkSupport();
  }, []);

  const handleStartRecording = async () => {
    if (!isSupported) {
      alert(errorMessage);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // Check if MediaRecorder is supported
      if (!window.MediaRecorder) {
        throw new Error('MediaRecorder is not supported in this browser.');
      }

      // Try to use a more compatible audio format
      let selectedFormat = { type: 'audio/webm;codecs=opus', ext: 'webm' };
      
      // Try different MIME types in order of preference for Whisper compatibility
      const supportedTypes = [
        { type: 'audio/wav', ext: 'wav' },
        { type: 'audio/mp4', ext: 'm4a' },
        { type: 'audio/webm;codecs=opus', ext: 'webm' },
        { type: 'audio/ogg;codecs=opus', ext: 'ogg' }
      ];
      
      for (const format of supportedTypes) {
        if (MediaRecorder.isTypeSupported(format.type)) {
          selectedFormat = format;
          break;
        }
      }
      
      console.log(`Using audio format: ${selectedFormat.type}`);

      mediaRecorderRef.current = new MediaRecorder(stream, { mimeType: selectedFormat.type });
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorderRef.current.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: selectedFormat.type });
        setAudioBlob(blob);
        console.log('Recorded audio blob:', blob);
        
        if (onSendVoice) {
          // Generate a unique filename with proper extension
          const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
          const filename = `voice-recording-${timestamp}.${selectedFormat.ext}`;
          onSendVoice({ 
            type: 'voice', 
            content: blob,
            name: filename
          });
        } else {
          alert('Voice recorded successfully! Check console for details.');
        }
        
        // Reset for next recording
        audioChunksRef.current = [];
        // Stop tracks to release microphone
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorderRef.current.onerror = (event) => {
        console.error('MediaRecorder error:', event.error);
        setErrorMessage('Recording failed: ' + event.error.message);
        setIsRecording(false);
        stream.getTracks().forEach(track => track.stop());
        
        // Notify parent component that recording stopped due to error
        if (onRecordingStateChange) {
          onRecordingStateChange(false);
        }
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
      setAudioBlob(null);
      setErrorMessage('');
      
      // Notify parent component that recording started
      if (onRecordingStateChange) {
        onRecordingStateChange(true);
      }
      
    } catch (err) {
      console.error('Error accessing microphone:', err);
      let userMessage = 'Error accessing microphone. ';
      
      if (err.name === 'NotAllowedError') {
        userMessage += 'Please allow microphone access and try again.';
      } else if (err.name === 'NotFoundError') {
        userMessage += 'No microphone found. Please connect a microphone.';
      } else if (err.name === 'NotSupportedError') {
        userMessage += 'Audio recording is not supported in this browser.';
      } else if (err.name === 'NotReadableError') {
        userMessage += 'Microphone is already in use by another application.';
      } else {
        userMessage += err.message || 'Unknown error occurred.';
      }
      
      setErrorMessage(userMessage);
      alert(userMessage);
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      // Notify parent component that recording stopped
      if (onRecordingStateChange) {
        onRecordingStateChange(false);
      }
    }
  };

  // Show warning icon if not supported
  if (!isSupported) {
    return (
      <Button
        variant="ghost"
        size="icon"
        type="button"
        disabled={true}
        className="h-8 w-8 text-red-500"
        title={errorMessage}
      >
        <AlertCircle className="h-4 w-4" />
      </Button>
    );
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      type="button"
      onClick={isRecording ? handleStopRecording : handleStartRecording}
      disabled={disabled}
      className={`h-8 w-8 ${isRecording ? 'text-red-500 hover:text-red-600' : 'text-muted-foreground hover:text-foreground'}`}
      title={isRecording ? 'Stop Recording' : 'Voice Input'}
    >
      {isRecording ? (
        <MicOff className="h-4 w-4" />
      ) : (
        <Mic className="h-4 w-4" />
      )}
    </Button>
  );
};

export default VoiceInput; 