from .base import BaseEngine, OCRResult
import time


class NougatEngine(BaseEngine):
    def __init__(self, config: dict = None):
        super().__init__(config)
        self.name = "Nougat"
        self._model = None

    def _patch_transformers_compat(self):
        from nougat.model import BARTDecoder

        if getattr(BARTDecoder.prepare_inputs_for_inference, "_ocr_harness_patched", False):
            return

        original = BARTDecoder.prepare_inputs_for_inference

        def patched(
            decoder_self,
            input_ids,
            encoder_outputs,
            past=None,
            past_key_values=None,
            use_cache=None,
            attention_mask=None,
            **kwargs,
        ):
            return original(
                decoder_self,
                input_ids=input_ids,
                encoder_outputs=encoder_outputs,
                past=past,
                past_key_values=past_key_values,
                use_cache=use_cache,
                attention_mask=attention_mask,
            )

        patched._ocr_harness_patched = True
        BARTDecoder.prepare_inputs_for_inference = patched

    def _get_model(self):
        if self._model is not None:
            return self._model

        from nougat import NougatModel
        from nougat.utils.checkpoint import get_checkpoint
        from nougat.utils.device import move_to_device
        import torch

        self._patch_transformers_compat()
        use_cuda = torch.cuda.is_available() and self.config.get("gpu", True)
        checkpoint = self.config.get("checkpoint")
        if checkpoint is None:
            checkpoint = get_checkpoint(None, model_tag=self.config.get("model", "0.1.0-small"))
        self._model = NougatModel.from_pretrained(checkpoint)
        self._model = move_to_device(self._model, bf16=use_cuda, cuda=use_cuda)
        self._model.eval()
        return self._model

    async def convert(self, pdf_path: str, **kwargs) -> OCRResult:
        start = time.time()
        try:
            from PIL import Image
            import fitz

            model = self._get_model()
            doc = fitz.open(pdf_path)
            texts = []
            for page_index in range(len(doc)):
                pix = doc[page_index].get_pixmap(dpi=kwargs.get("dpi", 150))
                image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                output = model.inference(image=image)
                predictions = output.get("predictions", []) if isinstance(output, dict) else []
                if predictions:
                    texts.append(predictions[0])
            doc.close()
            return OCRResult(markdown="\n\n".join(texts), engine=self.name, processing_time=time.time() - start)
        except ImportError as exc:
            return OCRResult(success=False, error=f"Nougat not installed ({exc}). Run: pip install nougat-ocr", engine=self.name)
        except Exception as e:
            return OCRResult(success=False, error=str(e), engine=self.name, processing_time=time.time() - start)

    async def is_available(self) -> bool:
        try:
            import nougat
            return True
        except ImportError:
            return False

    def get_metadata(self) -> dict:
        return {"name": "Nougat", "gpu": self.config.get("gpu", True), "lang": "en"}
