import logging
import wave
import sys

from . import metasentence
from . import recognizer
from . import diff_align
from . import transcription
from .transcriber import Transcriber as transcriber
'''The script will rework.
Multipass realign unaligned words.
Prepare multipass checking words sequence, when word's case ==
not-found-in-audio preparing chunk to realign like [words before, unaligned
words, words after], using new recognizer and transcriber for the chunk, putting back into result sequence.
'''
def prepare_multipass(alignment):
    to_realign = []
    chunks = 0

    for i, w in enumerate(alignment):
        if w.case == 2 or w.case == 3:
            for j, wd in enumerate(alignment):
                if j >= max(0, i-3) and j <= min(len(alignment), i+3):
                    wd.realign = True
    cur_list = []
    start_idx = []
    end_idx = []
    start_counter = 0
    end_counter = 0

    for j, wd in enumerate(alignment):
        if wd.realign:
            cur_list.append(wd)

        else:
            if len(cur_list) != 0:
                to_realign.append(cur_list)
                cur_list = []
                chunks += 1

    if len(cur_list) != 0:
        to_realign.append(cur_list)
        chunks += 1

    return to_realign, chunks

def realign(alignment, ms, model, progress_cb=None):
    to_realign, chunks = prepare_multipass(alignment)
    tasks = []

    def realign(chunk):
        realignments = []
        wavfile = wave.open(sys.argv[1], "rb")
        shift_start = 0.5
        shift_end = 2
        start_t = chunk[0].start
        end_t = chunk[-1].end
        duration = end_t - start_t
        chunk_start_word = chunk[0].word
        chunk_end_word = chunk[-1].word

        # set start/end to get chunk's text part
        chunk_start = chunk[0].startOffset
        chunk_end = chunk[-1].endOffset
        chunk_transcript = ms.raw_sentence[chunk_start:chunk_end]
        chunk_ms = metasentence.MetaSentence(chunk_transcript, model)
        chunk_ks = chunk_ms.get_kaldi_sequence()
        chunk_length = len(chunk_ks)

        # getting chunk's sound part as value 'words'
        chunk_recognizer = recognizer.recognize(chunk_transcript + '.', model)
        start_pos = int(((start_t - shift_start) * wavfile.getframerate()))
        wavfile.setpos(start_pos)
        end_pos = int(((2 * duration) + shift_end) * wavfile.getframerate())
        chunk_end = end_pos + start_pos
        words = transcriber.transcribe(chunk_recognizer, wavfile, chunk_end)[0:chunk_length + 1]

        if words[0]['word'] != chunk_start_word:
            words = words[1:len(words)]

        if words[-1]['word'] != chunk_end_word:
            words = words[0:len(words) - 1]
        
        start_t_chunk = words[0]['start']
        for i in range(len(words)):
            words[i]['start'] = words[i]['start'] - start_t_chunk + start_t
            words[i]['end'] = words[i]['end'] - start_t_chunk + start_t
        
        word_alignment = diff_align.align(words, chunk_ms)
        realignments.append({"chunk": chunk, "words": word_alignment})
        return realignments

    for i in range(chunks):
        tasks.extend(realign(to_realign[i]))

    output_words = alignment
    for i, obj in enumerate(tasks):
        start_task = output_words.index(tasks[i]["chunk"][0])
        duration_task = len(tasks[i]["chunk"])
        output_words = output_words[:start_task] + tasks[i]["words"]  + output_words[start_task + duration_task:]

    return output_words
