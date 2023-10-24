# Automatic Checkpointing to S3

To automatically store checkpoints in S3, callbacks provided by the trainer class can be leveraged.
They are automatically called at certain points during training and make it easy to extend the default trainer functionality without having to extend the trainer base class.
A callback is provided in `checkpoint_s3_saver.py`, which simply uploads the checkpoint output directory to S3 after a save (following the same pattern as the built-in huggingface hub integration):

```python
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

```
To simplify setup of the callback and make it possible to catch errors, a contextmanager is also provided:
```python
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

```

Using this context manager, adding S3 save functionality is as simple as wrapping the training loop using the following syntax:

```python
trainer = Trainer(...)

with checkpoint_saver(
    s3_path="s3://bucket-name/path/to/save/checkpoints",
    trainer=trainer,
    save_model=True,
):
    trainer.train(resume_from_checkpoint=...)
```
Any errors trigger a final model save and upload to S3 before passing the error back to the caller.