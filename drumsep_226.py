"""MusicSense 226: modelo DrumSep treinado para bombo, caixa, pratos e tons.

Modelo: model_drumsep.th, ZFTurbo/Music-Source-Separation-Training v1.0.5.
Executa separacao verdadeira via hdemucs, nao filtros de frequencia.
"""
import argparse
import subprocess
import tempfile
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from demucs.apply import apply_model

BASE = Path(__file__).resolve().parent
FF = Path(r"C:\Yt-dlp\ffmpeg.exe")
MODEL = BASE / "models_226" / "model_drumsep.th"
SOURCE_KEYS = ("kick", "snare", "cymbals", "toms")


def run(input_path, output_folder):
    if not MODEL.is_file() or MODEL.stat().st_size < 10000000:
        raise RuntimeError("Modelo detalhado de bateria indisponivel")
    output_folder.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(min(8, max(2, torch.get_num_threads())))
    print("STAGE 1 Carregando modelo DrumSep", flush=True)
    # Checkpoint original publicado pelos desenvolvedores e fixado nesta pasta.
    checkpoint = torch.load(MODEL, map_location="cpu", weights_only=False)
    model = checkpoint["klass"](*checkpoint["args"], **checkpoint["kwargs"])
    model.load_state_dict(checkpoint["state"], strict=True)
    model.eval()

    with tempfile.TemporaryDirectory(prefix="ms_drumsep_pcm_") as temp:
        wav = Path(temp) / "drums_44100.wav"
        cmd = [str(FF), "-hide_banner", "-loglevel", "error", "-y",
               "-i", str(input_path), "-vn", "-ar", "44100", "-ac", "2",
               "-c:a", "pcm_f32le", str(wav)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode:
            raise RuntimeError("Nao foi possivel converter a bateria: " + proc.stderr[-300:])
        audio, sample_rate = sf.read(wav, dtype="float32", always_2d=True)
        if audio.shape[0] < 44100 or audio.shape[1] != 2:
            raise RuntimeError("Arquivo de bateria invalido")
        mixed = torch.from_numpy(np.ascontiguousarray(audio.T))
        means = mixed.mean(dim=0)
        # Mesmo procedimento de normalizacao utilizado pelo Demucs.
        ref = mixed.mean(dim=0)
        avg = ref.mean()
        std = ref.std().clamp(min=1e-5)
        normalized = (mixed - avg) / std
        print("STAGE 2 Separando quatro componentes de bateria", flush=True)
        with torch.inference_mode():
            predictions = apply_model(model, normalized[None], shifts=1,
                                      split=True, overlap=0.35,
                                      device=torch.device("cpu"), progress=False)[0]
            predictions = predictions * std + avg
        print("STAGE 3 Validando as trilhas extraidas", flush=True)
        energy = float(torch.sqrt((mixed**2).mean()).item())
        outputs = {}
        for index, key in enumerate(SOURCE_KEYS):
            component = predictions[index].T.cpu().contiguous().numpy()
            rms = float(np.sqrt(np.mean(component * component)))
            # Nao inventa instrumento se o modelo praticamente nao detectou sinal.
            if rms < max(0.00018, energy * .026):
                print(f"SKIPPED {key} {rms:.6f}", flush=True)
                continue
            path = output_folder / f"{key}.wav"
            sf.write(str(path), component, sample_rate, subtype="PCM_24")
            outputs[key] = str(path)
            print(f"STEM {key} {rms:.6f}", flush=True)
        if not outputs:
            raise RuntimeError("Modelo nao identificou componentes de bateria audiveis")
        print("STAGE 4 Trilhas de bateria prontas", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        run(args.input, args.output)
    except Exception as exc:
        print("ERROR " + str(exc), file=sys.stderr, flush=True)
        raise
