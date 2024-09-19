class Transcription:

    def __init__(self):
        self.en_cours = ""
        self.entier = []

    def validation(self):
        self.entier.append(self.en_cours)
        self.en_cours = ""

    def update(self, message):
        self.en_cours = message

    def clear(self):
        self.en_cours = ""
        self.entier = []
    
    def get(self) -> str :
        str = ""
        for phrase in self.entier:
            str += f"{phrase}"
        print (f"str = '{str}'")
        return (str)