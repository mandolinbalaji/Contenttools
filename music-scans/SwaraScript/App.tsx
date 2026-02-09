
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { GoogleGenAI, LiveServerMessage, Modality } from '@google/genai';
import { Swara, SwaraEntry, ConnectionStatus } from './types';
import { createPcmBlob, decode, decodeAudioData } from './utils/audioUtils';
import Visualizer from './components/Visualizer';
import SwaraCard from './components/SwaraCard';

const App: React.FC = () => {
  const [status, setStatus] = useState<ConnectionStatus>(ConnectionStatus.IDLE);
  const [notation, setNotation] = useState<SwaraEntry[]>([]);
  const [rawNotationText, setRawNotationText] = useState<string>("");
  const [viewMode, setViewMode] = useState<'cards' | 'text'>('text');
  const [micStream, setMicStream] = useState<MediaStream | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastHeard, setLastHeard] = useState<string>("");
  const [isReading, setIsReading] = useState(false);
  const [isProcessingFile, setIsProcessingFile] = useState(false);
  const [fileProgress, setFileProgress] = useState(0);
  const [debugLogs, setDebugLogs] = useState<{msg: string, type: 'info' | 'vocal' | 'system' | 'error'}[]>([]);
  
  // Device Selection States
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState<string>("");
  const [showDevicePicker, setShowDevicePicker] = useState(false);

  const audioContextRef = useRef<AudioContext | null>(null);
  const sessionRef = useRef<any>(null);
  const logContainerRef = useRef<HTMLDivElement>(null);
  const scriptProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const addLog = (log: string, type: 'info' | 'vocal' | 'system' | 'error' = 'info') => {
    setDebugLogs(prev => [...prev, { msg: log, type }].slice(-100));
  };

  // Fetch audio devices
  const refreshDevices = useCallback(async () => {
    try {
      const allDevices = await navigator.mediaDevices.enumerateDevices();
      const audioInputs = allDevices.filter(device => device.kind === 'audioinput');
      setDevices(audioInputs);
      if (audioInputs.length > 0 && !selectedDeviceId) {
        setSelectedDeviceId(audioInputs[0].deviceId);
      }
    } catch (err) {
      console.error("Error enumerating devices", err);
    }
  }, [selectedDeviceId]);

  useEffect(() => {
    refreshDevices();
    // Listen for device changes
    navigator.mediaDevices.addEventListener('devicechange', refreshDevices);
    return () => navigator.mediaDevices.removeEventListener('devicechange', refreshDevices);
  }, [refreshDevices]);

  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [debugLogs]);

  const clearNotation = () => {
    setNotation([]);
    setRawNotationText("");
    setLastHeard("");
    setDebugLogs([]);
    setFileProgress(0);
    addLog("Notation cleared.", "system");
  };

  const copyToClipboard = () => {
    if (!rawNotationText) return;
    const cleanText = rawNotationText.toLowerCase().replace(/[^srgmpdn]/g, '').trim();
    navigator.clipboard.writeText(cleanText).then(() => {
      addLog("Notation copied to clipboard.", "system");
    });
  };

  const readInTamil = async () => {
    if (!rawNotationText || isReading) return;
    setIsReading(true);
    addLog("Converting to Tamil speech...", "system");
    try {
      const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
      const tamilMapping: Record<string, string> = {
        's': 'ஸ', 'r': 'ரி', 'g': 'க', 'm': 'ம', 'p': 'ப', 'd': 'த', 'n': 'நி'
      };
      
      const cleanNotation = rawNotationText.toLowerCase().replace(/[^srgmpdn]/g, '');
      const tamilSwaras = cleanNotation.split('').map(char => tamilMapping[char] || char).join(' ');
      
      const response = await ai.models.generateContent({
        model: "gemini-2.5-flash-preview-tts",
        contents: [{ parts: [{ text: `Clearly speak these swaras in Tamil: ${tamilSwaras}` }] }],
        config: {
          responseModalities: [Modality.AUDIO],
          speechConfig: {
            voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Kore' } },
          },
        },
      });
      const audioBase64 = response.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
      if (audioBase64) {
        const ctx = new (window.AudioContext || (window as any).webkitAudioContext)({sampleRate: 24000});
        const buffer = await decodeAudioData(decode(audioBase64), ctx, 24000, 1);
        const source = ctx.createBufferSource();
        source.buffer = buffer;
        source.connect(ctx.destination);
        source.onended = () => {
          setIsReading(false);
          ctx.close();
        };
        source.start();
      } else { 
        setIsReading(false); 
      }
    } catch (error) {
      setIsReading(false);
      addLog("Speech playback failed.", "error");
    }
  };

  const processTextForSwaras = useCallback((text: string, isFromMic = false) => {
    const cleanText = text.toUpperCase();
    const swaraMap: Record<string, string> = {
      'SA': 's', 'SAA': 's', 'CHA': 's', 'CHAA': 's', 'S': 's',
      'RI': 'r', 'REE': 'r', 'RE': 'r', 'RU': 'r', 'R': 'r',
      'GA': 'g', 'GAA': 'g', 'G': 'g',
      'MA': 'm', 'MAA': 'm', 'M': 'm',
      'PA': 'p', 'PAA': 'p', 'P': 'p',
      'DA': 'd', 'DHA': 'd', 'DHAA': 'd', 'D': 'd',
      'NI': 'n', 'NEE': 'n', 'N': 'n'
    };
    
    const tokens = cleanText.match(/(SA|SAA|CHA|CHAA|RI|REE|RE|RU|GA|GAA|MA|MAA|PA|PAA|DA|DHA|DHAA|NI|NEE|[SRGMPDN])/g) || [];
    const found: string[] = [];

    tokens.forEach(token => {
      if (swaraMap[token]) {
        found.push(swaraMap[token]);
      }
    });
    
    if (found.length > 0) {
      const swaraStr = found.join("");
      setRawNotationText(prev => prev + swaraStr);
      setNotation(prev => [...prev, ...found.map(s => ({
        id: Math.random().toString(36).substring(2, 9),
        swara: s.toUpperCase() as Swara,
        timestamp: Date.now()
      }))].slice(-500));
      
      addLog(`Detected: ${swaraStr}`, isFromMic ? 'vocal' : 'info');
    }
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    
    setIsProcessingFile(true);
    setFileProgress(0);
    setLastHeard("Listening...");
    addLog(`Loading: ${file.name}`, "system");

    try {
      const arrayBuffer = await file.arrayBuffer();
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const audioBuffer = await ctx.decodeAudioData(arrayBuffer);
      
      const offlineCtx = new OfflineAudioContext(1, audioBuffer.duration * 16000, 16000);
      const sourceNode = offlineCtx.createBufferSource();
      sourceNode.buffer = audioBuffer;
      sourceNode.connect(offlineCtx.destination);
      sourceNode.start();
      const resampledBuffer = await offlineCtx.startRendering();
      const pcmData = resampledBuffer.getChannelData(0);

      const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
      const sessionPromise = ai.live.connect({
        model: 'gemini-2.5-flash-native-audio-preview-12-2025',
        config: {
          responseModalities: [Modality.AUDIO],
          systemInstruction: 'You are a Carnatic Music Swara Recognizer. Transcribe the singing into s, r, g, m, p, d, n. Output ONLY these lowercase letters. If you hear "Sa", output "s". If you hear "Ri", output "r". No words, no punctuation.',
          inputAudioTranscription: {},
          outputAudioTranscription: {},
        },
        callbacks: {
          onmessage: (msg: LiveServerMessage) => {
            const outText = msg.serverContent?.outputTranscription?.text || "";
            const inText = msg.serverContent?.inputTranscription?.text || "";
            const combined = (outText + inText).trim();
            if (combined) {
              setLastHeard(combined.toLowerCase());
              processTextForSwaras(combined, false);
            }
          },
          onerror: (err) => {
            addLog(`Error: ${err.message}`, "error");
            setIsProcessingFile(false);
          },
          onclose: () => {
            setIsProcessingFile(false);
            setLastHeard("");
            addLog("Finished analyzing file.", "system");
          }
        }
      });

      const session = await sessionPromise;
      const CHUNK_SIZE = 8000; 
      let offset = 0;

      while (offset < pcmData.length) {
        if (!isProcessingFile) break; 
        const end = Math.min(offset + CHUNK_SIZE, pcmData.length);
        const chunk = pcmData.slice(offset, end);
        session.sendRealtimeInput({ media: createPcmBlob(chunk) });
        offset = end;
        
        const progress = Math.round((offset / pcmData.length) * 100);
        setFileProgress(progress);
        await new Promise(r => setTimeout(r, 150));
      }
      
      setTimeout(() => {
        session.close();
        setIsProcessingFile(false);
      }, 4000);
    } catch (err: any) {
      addLog(`Failed: ${err.message}`, "error");
      setIsProcessingFile(false);
      setLastHeard("");
    }
  };

  const stopTranscription = useCallback(async () => {
    addLog("Microphone session ended.", "system");
    if (scriptProcessorRef.current) scriptProcessorRef.current.disconnect();
    if (sessionRef.current) try { await sessionRef.current.close(); } catch (e) {}
    if (audioContextRef.current) try { await audioContextRef.current.close(); } catch (e) {}
    if (micStream) micStream.getTracks().forEach(track => track.stop());
    setMicStream(null);
    setStatus(ConnectionStatus.IDLE);
    setLastHeard("");
  }, [micStream]);

  const startTranscription = async () => {
    try {
      setStatus(ConnectionStatus.CONNECTING);
      
      const constraints: MediaStreamConstraints = { 
        audio: selectedDeviceId ? { deviceId: { exact: selectedDeviceId } } : true 
      };
      
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      
      // If we didn't have device labels before, we likely have them now
      if (devices.some(d => !d.label)) {
        refreshDevices();
      }

      setMicStream(stream);
      const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
      const inputCtx = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
      audioContextRef.current = inputCtx;
      
      const sessionPromise = ai.live.connect({
        model: 'gemini-2.5-flash-native-audio-preview-12-2025',
        config: {
          responseModalities: [Modality.AUDIO],
          systemInstruction: `You are a Carnatic Music Swara Recognizer. Transcribe vocals into s, r, g, m, p, d, n. Output ONLY these lowercase letters. No words.`,
          outputAudioTranscription: {},
          inputAudioTranscription: {},
        },
        callbacks: {
          onopen: () => {
            setStatus(ConnectionStatus.CONNECTED);
            addLog("Mic Live. Transcribing...", "system");
            const source = inputCtx.createMediaStreamSource(stream);
            const scriptProcessor = inputCtx.createScriptProcessor(4096, 1, 1);
            scriptProcessorRef.current = scriptProcessor;
            scriptProcessor.onaudioprocess = (e) => {
              sessionPromise.then(s => s.sendRealtimeInput({ media: createPcmBlob(e.inputBuffer.getChannelData(0)) }));
            };
            source.connect(scriptProcessor);
            scriptProcessor.connect(inputCtx.destination);
          },
          onmessage: (msg: LiveServerMessage) => {
            const outText = msg.serverContent?.outputTranscription?.text || "";
            const inText = msg.serverContent?.inputTranscription?.text || "";
            const txt = (outText + inText).trim();
            if (txt) {
              setLastHeard(txt.toLowerCase());
              processTextForSwaras(txt, true);
            }
          },
          onerror: (err) => {
            addLog(`Error: ${err.message}`, "error");
            stopTranscription();
          },
          onclose: () => {
            setStatus(ConnectionStatus.IDLE);
            setLastHeard("");
          }
        }
      });
      sessionRef.current = await sessionPromise;
    } catch (err) {
      setErrorMessage("Mic access failed.");
      setStatus(ConnectionStatus.ERROR);
      addLog("Could not access microphone. Please check permissions.", "error");
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center pt-6 pb-24 px-4 bg-[#0b1120] text-slate-100 font-sans selection:bg-amber-500/40">
      <header className="text-center mb-4 w-full max-w-2xl">
        <h1 className="font-cinzel text-3xl md:text-4xl font-bold tracking-tight bg-gradient-to-r from-amber-100 to-amber-600 bg-clip-text text-transparent">SwarāScript</h1>
        <div className="flex items-center justify-center gap-2 mt-1">
          <div className={`w-1.5 h-1.5 rounded-full ${status === ConnectionStatus.CONNECTED || isProcessingFile ? 'bg-green-500 animate-pulse' : 'bg-slate-700'}`}></div>
          <span className="text-[8px] text-slate-500 uppercase tracking-[0.3em] font-black">Carnatic Swara Transcription</span>
        </div>
      </header>

      <div className="max-w-4xl w-full flex flex-col gap-4">
        {isProcessingFile && (
          <div className="w-full bg-slate-900/80 p-3 rounded-xl border border-amber-500/30 shadow-2xl animate-in fade-in slide-in-from-top-2">
            <div className="flex justify-between text-[10px] font-black uppercase text-amber-500 mb-1.5 px-1">
              <span className="flex items-center gap-2"><i className="fa-solid fa-spinner animate-spin"></i> Processing: {fileProgress}%</span>
              <span>{rawNotationText.length} Notes</span>
            </div>
            <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-amber-600 to-amber-400 transition-all duration-300" style={{width: `${fileProgress}%`}}></div>
            </div>
          </div>
        )}

        <div className="flex flex-wrap justify-between items-center bg-slate-900/40 p-1.5 rounded-xl border border-slate-800/50 backdrop-blur-xl">
          <div className="flex gap-1">
            <button onClick={() => setViewMode('text')} className={`px-4 py-1.5 rounded-lg text-[9px] font-black transition-all ${viewMode === 'text' ? 'bg-amber-500 text-slate-950 shadow-lg' : 'text-slate-400'}`}>EDITOR</button>
            <button onClick={() => setViewMode('cards')} className={`px-4 py-1.5 rounded-lg text-[9px] font-black transition-all ${viewMode === 'cards' ? 'bg-amber-500 text-slate-950 shadow-lg' : 'text-slate-400'}`}>CARDS</button>
          </div>
          <div className="flex gap-3 px-3">
            <button 
              onClick={readInTamil} 
              disabled={isReading || !rawNotationText} 
              className={`text-[9px] uppercase font-black text-amber-500 flex items-center gap-1.5 transition-opacity ${isReading || !rawNotationText ? 'opacity-30 cursor-not-allowed' : 'hover:text-amber-400'}`}
            >
              <i className={`fa-solid ${isReading ? 'fa-spinner animate-spin' : 'fa-volume-high'}`}></i> SPEAK TAMIL
            </button>
            <button onClick={copyToClipboard} className="text-[9px] uppercase font-black text-slate-500 hover:text-amber-400 transition-colors flex items-center gap-1.5"><i className="fa-solid fa-copy"></i> COPY</button>
            <button onClick={clearNotation} className="text-[9px] uppercase font-black text-slate-500 hover:text-red-400 transition-colors flex items-center gap-1.5"><i className="fa-solid fa-rotate"></i> RESET</button>
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-[1.5rem] shadow-2xl h-[45vh] relative overflow-hidden flex flex-col backdrop-blur-md">
          {lastHeard && (
             <div className="absolute top-4 right-6 pointer-events-none z-10 animate-in fade-in slide-in-from-right-4">
               <div className="text-[10px] font-mono px-3 py-1 rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/30 backdrop-blur-md">
                 HEARING: {lastHeard.toUpperCase()}
               </div>
             </div>
          )}
          <div className="flex-1 p-6 overflow-y-auto custom-scrollbar">
            {viewMode === 'text' ? (
              <textarea
                value={rawNotationText}
                onChange={(e) => setRawNotationText(e.target.value.toLowerCase().replace(/[^srgmpdn\s]/g, ''))}
                placeholder={isProcessingFile ? "Transcribing file..." : "Start singing or upload an audio file..."}
                className="w-full h-full bg-transparent border-none focus:ring-0 text-xl md:text-2xl font-mono text-amber-100 placeholder:text-slate-800/40 resize-none leading-relaxed tracking-tighter"
                spellCheck={false}
              />
            ) : (
              <div className="flex flex-wrap gap-1.5 content-start h-full">
                {notation.length === 0 ? <div className="w-full h-full flex items-center justify-center opacity-5 uppercase text-[10px] tracking-[0.5em]">No Data</div> : notation.map(e => <SwaraCard key={e.id} swara={e.swara} timestamp={e.timestamp} />)}
              </div>
            )}
          </div>
        </div>

        <div className="bg-black/30 border border-slate-800/50 rounded-lg h-24 overflow-hidden shadow-inner">
           <div 
             ref={logContainerRef} 
             className="h-full overflow-y-auto p-3 font-mono text-[9px] leading-tight custom-scrollbar bg-slate-950/10"
           >
             {debugLogs.length === 0 && <div className="text-slate-700 italic">Logs will appear here...</div>}
             {debugLogs.map((log, i) => (
               <div key={i} className={`mb-0.5 flex gap-2 ${log.type === 'vocal' ? 'text-amber-400 font-bold' : log.type === 'system' ? 'text-slate-500 italic' : log.type === 'error' ? 'text-red-500' : 'text-slate-600'}`}>
                 <span className="opacity-10 shrink-0">{new Date().toLocaleTimeString([], {hour12: false, second: '2-digit'})}</span>
                 <span className="flex-1">{log.msg}</span>
               </div>
             ))}
           </div>
        </div>
      </div>

      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 w-full max-w-[320px] flex flex-col gap-3 z-50 px-4">
        {showDevicePicker && (
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-3 shadow-2xl animate-in fade-in slide-in-from-bottom-4 mb-2">
            <h3 className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2 px-1">Choose Microphone</h3>
            <div className="flex flex-col gap-1 max-h-48 overflow-y-auto custom-scrollbar">
              {devices.map(device => (
                <button
                  key={device.deviceId}
                  onClick={() => {
                    setSelectedDeviceId(device.deviceId);
                    setShowDevicePicker(false);
                    if (status === ConnectionStatus.CONNECTED) {
                      stopTranscription().then(() => startTranscription());
                    }
                  }}
                  className={`text-left px-3 py-2 rounded-lg text-[10px] transition-colors ${selectedDeviceId === device.deviceId ? 'bg-amber-500 text-slate-900 font-bold' : 'text-slate-300 hover:bg-slate-800'}`}
                >
                  {device.label || `Microphone ${device.deviceId.slice(0, 5)}`}
                </button>
              ))}
              {devices.length === 0 && <div className="text-[10px] text-slate-500 p-2 italic">No microphones found</div>}
            </div>
          </div>
        )}

        <div className={`w-full transition-all duration-500 ${status === ConnectionStatus.CONNECTED ? 'opacity-100 translate-y-0 scale-100' : 'opacity-0 translate-y-2 scale-95 pointer-events-none'}`}>
          <div className="bg-slate-900/95 border border-slate-700 p-1.5 rounded-xl shadow-2xl backdrop-blur-md"><Visualizer stream={micStream} isActive={status === ConnectionStatus.CONNECTED} /></div>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={() => setShowDevicePicker(!showDevicePicker)}
            className={`w-14 h-14 rounded-full border transition-all flex items-center justify-center shadow-xl ${showDevicePicker ? 'bg-amber-500 border-amber-500 text-slate-950' : 'bg-slate-800 border-slate-700 text-slate-400'}`}
            title="Choose audio device"
          >
            <i className="fa-solid fa-microphone-lines text-lg"></i>
          </button>
          
          <button
            onClick={status === ConnectionStatus.CONNECTED ? stopTranscription : startTranscription}
            disabled={status === ConnectionStatus.CONNECTING || isProcessingFile}
            className={`flex-1 h-14 rounded-full font-black text-[10px] tracking-[0.3em] transition-all shadow-xl active:scale-95 ${status === ConnectionStatus.CONNECTED ? 'bg-red-500 text-white shadow-red-500/20' : 'bg-amber-500 text-slate-950 shadow-amber-500/20'}`}
          >
            {status === ConnectionStatus.CONNECTING ? <i className="fa-spin fa-solid fa-spinner"></i> : status === ConnectionStatus.CONNECTED ? 'STOP MIC' : 'LIVE MIC'}
          </button>
          
          <button 
            onClick={() => fileInputRef.current?.click()}
            disabled={status === ConnectionStatus.CONNECTED || isProcessingFile}
            className="w-14 h-14 rounded-full bg-slate-800 border border-slate-700 text-slate-400 hover:text-amber-400 hover:border-amber-500/50 transition-all flex items-center justify-center disabled:opacity-20 shadow-xl"
            title="Upload audio"
          >
            <i className={`fa-solid ${isProcessingFile ? 'fa-spinner animate-spin' : 'fa-file-audio'} text-lg`}></i>
          </button>
        </div>
        <input ref={fileInputRef} type="file" accept="audio/*" onChange={handleFileUpload} className="hidden" />
      </div>

      <style>{`
        .custom-scrollbar::-webkit-scrollbar { width: 3px; height: 3px; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #1e293b; border-radius: 10px; }
        textarea:focus { outline: none !important; border: none !important; box-shadow: none !important; }
      `}</style>
    </div>
  );
};

export default App;
