"""MusicSense 229: etapa isolada de separacao voz principal / apoios vocais."""
import argparse
import hashlib
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODEL = ROOT / "models_229" / "UVR_MDXNET_KARA_2.onnx"
EXPECTED_SHA = "bf32e15105a09c0f7dddd2b67346146334d6f3ecb399ed7638eba2ab07cbf5f4"


def process(source, output):
    if not MODEL.is_file() or MODEL.stat().st_size < 50_000_000:
        raise RuntimeError("Modelo de apoio vocal ausente")
    # Evita arquivo alterado ou baixado parcialmente, sem acesso a rede durante a separacao.
    if hashlib.sha256(MODEL.read_bytes()).hexdigest() != EXPECTED_SHA:
        raise RuntimeError("Modelo de voz nao passou na verificacao de integridade")
    from audio_separator.separator import Separator
    print("STAGE 15 Validando modelo de karaokê", flush=True)
    import onnxruntime as ort
    providers = ort.get_available_providers()
    use_dml = "DmlExecutionProvider" in providers
    separator = Separator(
        log_level=logging.WARNING, model_file_dir=str(MODEL.parent),
        output_dir=str(output), output_format="WAV",
        mdx_params={"hop_length": 1024, "segment_size": 256,
                    "overlap": 0.15, "batch_size": 1, "enable_denoise": False})
    if use_dml:
        # A GPU acelera somente este subprocesso, sem alterar o Demucs rapido.
        separator.onnx_execution_provider = ["DmlExecutionProvider", "CPUExecutionProvider"]
        original_session = ort.InferenceSession
        def dml_session(*args, **kwargs):
            opts = kwargs.get("sess_options") or ort.SessionOptions()
            opts.enable_mem_pattern = False
            opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            kwargs["sess_options"] = opts
            return original_session(*args, **kwargs)
        ort.InferenceSession = dml_session
    print("STAGE 12 Dispositivo vocal: " + ("GPU DirectML" if use_dml else "CPU"), flush=True)
    separator.load_model(MODEL.name)
    print("STAGE 25 Modelo vocal carregado; separando voz principal e apoios", flush=True)
    result = separator.separate(str(source))
    if len(result) != 2:
        raise RuntimeError("Modelo vocal nao retornou exatamente duas trilhas")
    for name in result:
        file = Path(name)
        if not file.is_absolute():
            file = output / file
        print("OUTPUT " + str(file.resolve()), flush=True)
    print("STAGE 83 Dois canais vocais processados", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    try:
        process(args.input, args.output)
    except Exception as e:
        print("ERROR " + str(e), file=sys.stderr, flush=True)
        raise
