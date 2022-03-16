import os
import logging
import sys
import argparse

from transcriber import Transcriber as transcriber
from multiprocessing.dummy import Pool


parser = argparse.ArgumentParser(
        description = 'The program transcripts audiofile and displays result in selected format')
parser.add_argument(
        '-model', type=str,
        help='model path')
parser.add_argument(
        '-list_models', action='store_true', 
        help='list of all models')
parser.add_argument(
        '-model_name',  type=str,
        help='select model current language type')
parser.add_argument(
        '-lang',  default='en-us', type=str,
        help='smallest available model for selected language')
parser.add_argument(
        'input', type=str,
        help='audiofile')
parser.add_argument(
        '-output', default='', type=str,
        help='optional output filename path')
parser.add_argument(
        '-otype', '--outputtype', default='txt', type=str,
        help='optional arg output data type')
parser.add_argument(
        '--log', default='INFO',
        help='logging level')

args = parser.parse_args()
log_level = args.log.upper()
logging.getLogger().setLevel(log_level)
logging.info('checking input args')

def calculate(model, inputdata, outputdata, outputtype, log):
    logging.info('converting audiofile to 16K sampled wav')
    process = transcriber.resample_ffmpeg(inputdata)
    logging.info('complite')
    logging.info('starting transcription')
    final_result, tot_samples= transcriber.transcribe(model, process, outputdata, outputtype)
    logging.info('complite')
    if outputdata:
        with open(outputdata, 'w', encoding='utf-8') as fh:
            fh.write(final_result)
        logging.info('output writen to %s' % (outputdata))
    else:
        print(final_result)
    return final_result, tot_samples

def main(model, inputdata, outputdata, outputtype, list_models, model_name, lang, log):
    try:
        model = transcriber.get_model(lang, model_name)
    except Exception:
        logging.info('-lang or -model_name settings are wrong, try again')
        exit(1)
    if list_models:
        transcriber.get_list_models()
    if os.path.isdir(inputdata) and os.path.isdir(outputdata):
            arg_list = transcriber.process_dir(model, inputdata, outputdata, outputtype, log)
            with Pool() as pool:
                for final_result, tot_samples in pool.starmap(calculate, arg_list):
                    return final_result, tot_samples
    elif os.path.isfile(inputdata):
        final_result, tot_samples = calculate(model, inputdata, outputdata, outputtype, log)
    return final_result, tot_samples

if __name__ == '__main__':
    start_time = transcriber.get_time()
    tot_samples = main(args.model, args.input, args.output, args.outputtype, args.list_models, args.model_name, args.lang, args.log)[1]
    diff_end_start, sec, mcsec = transcriber.send_time(start_time)
    print(f'''Script info: execution time: {sec} sec, {mcsec} mcsec; xRT: {format(tot_samples / 16000.0 / float(diff_end_start), '.3f')}''')
