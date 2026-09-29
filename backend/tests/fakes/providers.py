class FakeEmbedder:
    def __init__(self, vector):
        self.vector = vector

    def embed_many(self, texts):
        return [self.vector for _ in texts]


class FakeGenerator:
    def generate(self, question, context):
        return f"测试答案：{context[:100]}"

