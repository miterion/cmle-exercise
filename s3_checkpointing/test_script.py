from checkpoint_saver import checkpoint_saver
from dataclasses import dataclass

@dataclass
class MockTrainer:
    def _get_output_dir(self):
        return "output_dir"
    def save_model(self, output_dir):
        print(f"Saving model to {output_dir}")

with checkpoint_saver(
    s3_path="s3://bucket-name/path/to/save/checkpoints",
    trainer=MockTrainer(),
    save_model=True,
):
    print("Training model...")
    raise ValueError("Something went wrong!")