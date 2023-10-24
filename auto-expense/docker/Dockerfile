FROM --platform=linux/amd64 763104351884.dkr.ecr.us-east-2.amazonaws.com/huggingface-pytorch-inference:2.0.0-transformers4.28.1-cpu-py310-ubuntu20.04

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
  --mount=type=cache,target=/var/lib/apt,sharing=locked \
  apt update && apt install -y tesseract-ocr 
RUN --mount=type=cache,target=/root/.cache,sharing=locked \
    pip install pytesseract