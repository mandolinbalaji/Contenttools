
export type Swara = 'S' | 'R' | 'G' | 'M' | 'P' | 'D' | 'N';

export interface SwaraEntry {
  id: string;
  swara: Swara;
  timestamp: number;
}

export enum ConnectionStatus {
  IDLE = 'IDLE',
  CONNECTING = 'CONNECTING',
  CONNECTED = 'CONNECTED',
  ERROR = 'ERROR'
}
