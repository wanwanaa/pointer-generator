import pickle
import torch
import argparse
import numpy as np
from LCSTS_char.config import Config
from LSTM.ROUGE import rouge_score, write_rouge
from LSTM.save_load import load_model
from LCSTS_char.data_utils import index2sentence, load_data, load_embeddings
import pathlib

# filename
# result
filename_result = 'result/summary/'
# rouge
filename_rouge = 'result/summary/ROUGE.txt'
# initalization
pathlib.Path(filename_rouge).touch()


def test(config, epoch, model, args):
    # batch, dropout
    model = model.eval()

    # filename
    filename_test_text = config.filename_trimmed_test_text
    filename_test_summary = config.filename_trimmed_test_summary
    filename_idx2word = config.filename_index

    # data
    test = load_data(filename_test_text, filename_test_summary, args.batch_size, shuffle=False, num_works=2)

    # idx2word
    f = open(filename_idx2word, 'rb')
    idx2word = pickle.load(f)

    bos = config.bos
    s_len = config.summary_len
    r = []
    for batch in test:
        x, _ = batch
        if torch.cuda.is_available():
            x = x.cuda()
            # y = y.cuda()
        # model
        # attention
        if args.attention:
            h, encoder_outputs = model.encoder(x)
            out = (torch.ones(x.size(0)) * bos)
            result = []
            if args.coverage:
                cover_vector = torch.zeros((x.size(0), 1, config.seq_len)).type(torch.FloatTensor)
            else:
                cover_vector = None
            for i in range(s_len):
                out = out.type(torch.LongTensor)
                y = out
                h0 = h
                attn_weights, context, out, h = model.decoder(out, h, encoder_outputs, cover_vector)
                gen = model.output_layer(out).squeeze()
                if args.coverage:
                    cover_vector = cover_vector + attn_weights
                if args.point:
                    prob = model.pointer(context, h0, y)
                    final = model.final_distribution(attn_weights, x, gen, prob)
                else:
                    final = torch.nn.functional.softmax(gen, dim=1)
                out = torch.argmax(final, dim=1)
                result.append(out.numpy())
            result = np.transpose(np.array(result))

        # seq2seq
        else:
            h, _ = model.encoder(x)
            out = (torch.ones(x.size(0)) * bos)
            result = []
            for i in range(s_len):
                out = out.type(torch.LongTensor).view(-1, 1)
                out, h = model.decoder(out, h)
                out = torch.squeeze(model.output_layer(out))
                out = torch.nn.functional.softmax(out, dim=1)
                out = torch.argmax(out, dim=1)
                result.append(out.numpy())
            result = np.transpose(np.array(result))

        for i in range(result.shape[0]):
            # sen1 = index2sentence(list(x[i]), idx2word)
            sen = index2sentence(list(result[i]), idx2word)
            r.append(' '.join(sen))

    # write result
    filename_data = filename_result + 'summary_' + str(epoch) + '.txt'
    with open(filename_data, 'w', encoding='utf-8') as f:
        f.write('\n'.join(r))

    # ROUGE
    score = rouge_score(config.gold_summaries, filename_data)

    # write rouge
    write_rouge(filename_rouge, score, epoch)

    # print rouge
    print('epoch:', epoch, '|ROUGE-1 f: %.4f' % score['rouge-1']['f'],
          ' p: %.4f' % score['rouge-1']['p'],
          ' r: %.4f' % score['rouge-1']['r'])
    print('epoch:', epoch, '|ROUGE-2 f: %.4f' % score['rouge-2']['f'],
          ' p: %.4f' % score['rouge-2']['p'],
          ' r: %.4f' % score['rouge-2']['r'])
    print('epoch:', epoch, '|ROUGE-L f: %.4f' % score['rouge-l']['f'],
          ' p: %.4f' % score['rouge-l']['p'],
          ' r: %.4f' % score['rouge-l']['r'])


if __name__ == '__main__':
    config = Config()
    # input
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch_size', '-b', type=int, default=32, help='batch size for train')
    parser.add_argument('--hidden_size', '-s', type=int, default=500, help='dimension of  code')
    parser.add_argument('--epoch', '-e', type=int, default=20, help='number of training epochs')
    parser.add_argument('--num_layers', '-n', type=int, default=1, help='number of gru layers')
    parser.add_argument('--attention', '-a', action='store_true', default=False, help="whether to use attention")
    parser.add_argument('--pre_train', '-p', action='store_true', default=False, help="load pre-train embedding")
    parser.add_argument('--point', '-g', action='store_true', default=False, help="pointer-generator")
    parser.add_argument('--coverage', '-c', action='store_true', default=False, help="whether to use coverage mechanism")
    args = parser.parse_args()

    # ########test######## #
    # args.attention = True
    # args.point = True
    # args.coverage = True
    # ########test######## #

    # embeddings
    if args.pre_train:
        filename = config.filename_embeddings
        embeddings = load_embeddings(filename)
    else:
        embeddings = None

    # test
    for epoch in range(args.epoch):
        model = load_model(embeddings, epoch, config, args)
        test(config, epoch, model, args)
