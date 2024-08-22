class Transcription:

    def __init__(self):
        self.en_cours = ""
        self.entier = ""

    def validation(self):
        self.entier += self.en_cours
        self.en_cours = ""

    def update(self, message):
        self.en_cours = message

    def clear(self):
        self.en_cours = ""
        self.entier = ""
    
    def get(self) -> str :
        return (f"{self.entier}{self.en_cours}")