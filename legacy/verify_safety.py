from safety import ImmediateCrisisDetector

detector = ImmediateCrisisDetector()
print(detector.check("I want to kill myself"))
print(detector.check("I feel sad"))
