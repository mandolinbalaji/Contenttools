
import React, { useEffect, useRef } from 'react';

interface VisualizerProps {
  stream: MediaStream | null;
  isActive: boolean;
}

const Visualizer: React.FC<VisualizerProps> = ({ stream, isActive }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  // Fix: Added initial value 0 to useRef<number>() to satisfy TypeScript requirement of 1 argument.
  const animationRef = useRef<number>(0);

  useEffect(() => {
    if (!isActive || !stream || !canvasRef.current) return;

    const audioContext = new AudioContext();
    const source = audioContext.createMediaStreamSource(stream);
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);

    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d')!;

    const draw = () => {
      animationRef.current = requestAnimationFrame(draw);
      analyser.getByteFrequencyData(dataArray);

      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const barWidth = (canvas.width / bufferLength) * 2.5;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        const barHeight = (dataArray[i] / 255) * canvas.height;
        ctx.fillStyle = `rgb(245, 158, 11)`; // Saffron gold
        ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
        x += barWidth + 1;
      }
    };

    draw();

    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
      audioContext.close();
    };
  }, [isActive, stream]);

  return (
    <canvas 
      ref={canvasRef} 
      className="w-full h-12 rounded-lg bg-slate-800/50" 
      width={400} 
      height={48} 
    />
  );
};

export default Visualizer;
