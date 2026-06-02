import { useRef, useState, useEffect } from 'react';

interface FaceCaptureProps {
  onCapture: (blob: Blob) => void;
  onRetry: () => void;
  captured: Blob | null;
}

export default function FaceCapture({ onCapture, onRetry, captured }: FaceCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } })
      .then(s => {
        setStream(s);
        if (videoRef.current) videoRef.current.srcObject = s;
      })
      .catch(() => setError('请允许使用摄像头'));
    return () => {
      if (stream) {
        stream.getTracks().forEach(t => t.stop());
      }
    };
  }, []);

  const capture = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d')!.drawImage(video, 0, 0);
    canvas.toBlob(blob => { if (blob) onCapture(blob); }, 'image/jpeg');
  };

  if (error) return <div style={{ color: 'red', textAlign: 'center', padding: 20 }}>{error}</div>;

  return (
    <div style={{ textAlign: 'center' }}>
      {captured && (
        <img src={URL.createObjectURL(captured)} alt="captured" style={{ width: 300, borderRadius: 8 }} />
      )}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        style={{ width: 300, borderRadius: 8, display: captured ? 'none' : 'block' }}
      />
      <canvas ref={canvasRef} style={{ display: 'none' }} />
      <div style={{ marginTop: 12 }}>
        <button
          onClick={captured ? onRetry : capture}
          style={{
            padding: '8px 24px',
            background: '#1677ff',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            cursor: 'pointer',
            fontSize: 14,
          }}
        >
          {captured ? '重新拍摄' : '拍照'}
        </button>
      </div>
    </div>
  );
}
