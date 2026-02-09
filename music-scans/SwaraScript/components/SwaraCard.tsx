
import React from 'react';
import { Swara } from '../types';

interface SwaraCardProps {
  swara: Swara;
  timestamp: number;
}

const swaraColors: Record<Swara, string> = {
  'S': 'bg-red-500/80 text-white',
  'R': 'bg-orange-500/80 text-white',
  'G': 'bg-yellow-500/80 text-black',
  'M': 'bg-green-500/80 text-white',
  'P': 'bg-blue-500/80 text-white',
  'D': 'bg-indigo-500/80 text-white',
  'N': 'bg-purple-500/80 text-white',
};

const SwaraCard: React.FC<SwaraCardProps> = ({ swara }) => {
  return (
    <div className="flex flex-col items-center animate-in fade-in scale-95 duration-200">
      <div className={`${swaraColors[swara]} w-8 h-8 rounded-md flex items-center justify-center font-mono text-sm font-black shadow-md`}>
        {swara.toLowerCase()}
      </div>
    </div>
  );
};

export default SwaraCard;
