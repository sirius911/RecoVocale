from Mode import Mode

class ArrierePlanMode(Mode):
    def enter(self):
        self.root.withdraw()

    def exit(self):
        self.root.deiconify()
