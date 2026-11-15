"""Compatibilidade Demucs com torchaudio moderno, sem TorchCodec."""
import sys
import soundfile as sf
import torchaudio as ta

def save_audio_without_torchcodec(uri, src, sample_rate, channels_first=True, encoding=None, bits_per_sample=None, **kwargs):
    audio=src.detach().cpu().numpy()
    if channels_first and audio.ndim==2:audio=audio.T
    subtype='FLOAT' if encoding=='PCM_F' else ('PCM_24' if bits_per_sample==24 else 'PCM_32' if bits_per_sample==32 else 'PCM_16')
    sf.write(str(uri),audio,sample_rate,subtype=subtype)
ta.save=save_audio_without_torchcodec
from demucs.separate import main
if __name__=='__main__':
    main()
