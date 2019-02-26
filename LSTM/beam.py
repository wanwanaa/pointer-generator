import torch

class beam():
    def __init__(self, model, s_len, bos, beam_size):
        self.model = model
        self.s_len = s_len # summary length
        self.bos = bos
        self.beam_size = beam_size

        hyp = [] # The path at each time step
        scorce = [] # The score for each translation on the beam

    def get_prob(self, y, hidden):


    def beam_search(self):
        # init
        path = [[[self.bos], 0.0]]
        for i in range(self.s_len):
            candidate = []
            for j in range(len(path)):
                data = model.
