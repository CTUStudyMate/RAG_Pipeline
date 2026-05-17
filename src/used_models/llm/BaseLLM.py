class BaseLLM:
    def generate(self, prompt, images=None):
        raise NotImplementedError
    