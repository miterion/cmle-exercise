from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

import boto3
from transformers import Trainer, TrainerCallback, TrainerControl, TrainerState
from transformers.training_args import TrainingArguments


class S3LogCallback(TrainerCallback):
    def __init__(self, s3_path: str):
        self.s3_path = s3_path

    def on_save(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs,
    ):
        upload_checkpoint_to_s3(self.s3_path, args.output_dir)
        return super().on_save(args, state, control, **kwargs)


def upload_checkpoint_to_s3(s3_path: str, output_dir: str) -> None:
    parsed_url = urlparse(s3_path)
    bucket = parsed_url.netloc
    key = parsed_url.path.lstrip("/")
    s3 = boto3.resource("s3")
    bucket = s3.Bucket(bucket)
    for file in Path(output_dir).glob("**/*"):
        if file.is_file():
            bucket.upload_file(str(file), f"{key}/{file.relative_to(output_dir)}")


@contextmanager
def checkpoint_saver(s3_path: str, trainer: Trainer, save_model: bool = True):
    """Saves checkpoints to S3

    Args:
        s3_path (str): S3 URL to save checkpoints to
        trainer (Trainer): Trainer instance
        save_model (bool, optional): Whether to run `trainer.save_model` before uploading after an exception.
                                     Defaults to True.
    """
    output_dir = trainer._get_output_dir()
    trainer.add_callback(S3LogCallback(s3_path))
    try:
        yield
    finally:
        if trainer.is_world_process_zero():
            if save_model:
                trainer.save_model(output_dir)
                upload_checkpoint_to_s3(s3_path, output_dir)
