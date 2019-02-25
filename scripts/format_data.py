import os
import re
import pickle
import math
from ast import literal_eval as make_tuple


def get_bpm(sid):
	bpms = [135, 100, 111, 86, 135, 120, 122, 127, 70, 125, 90, 120, 103, 88, 132, 122, 97, 112, 130, 134, 98, 135, 132, 130, 103, 158, 124, 109, 103, 104, 129, 125, 108, 93, 170, 135, 184, 125, 73, 122, 200, 125, 163, 124, 77, 168, 94, 86, 100, 114, 104, 140, 132, 125, 74, 74, 70, 118, 98, 148, 121, 81, 126, 100, 76, 76, 88, 92, 62, 104, 70, 76, 144, 94, 108, 70, 120, 75, 92, 80, 90, 88, 140, 138, 98, 80, 90, 120, 134, 127, 124, 134, 90, 78, 161, 130, 91, 107, 73, 80]	
	sid = int(sid)
	bpm = bpms[sid-1]
	return bpm


def get_file_content(path):
	f = open(path)
	content = f.read()
	f.close()
	return content

def get_chords_file_song_id(filename):
	pat = "^N([0-9]*)-.*"
	m = re.match(pat, filename)
	song_id = m.group(1)
	return song_id

def get_f0_file_song_id(filename):
	pat = "^RM-P([0-9]*).MELODY.TXT"
	m = re.match(pat, filename)
	song_id = m.group(1)
	return song_id

def get_midi_file_song_id(filename):
	pat = "^([0-9]*).*"
	m = re.match(pat, filename)
	song_id = m.group(1)
	song_id = "{:>3}".format(song_id).replace(' ', '0')
	return song_id

def get_tick_per_beat(content):
		tpb_pat = "<TicksPerBeat>([0-9]*)</TicksPerBeat>"
		m = re.search(tpb_pat, content)
		if m == None:
			print("TicksPerBeat not defined in MIDI file!")
			return None
		tpb = m.group(1)
		return int(tpb)


# -----------------------------------------------------------------------------

def retrieve_chords_file_data(content, sid):
	""" I: content of chords file
		O: list of chord labels per beat
	"""

	data = [row.split('\t') for row in content.split('\n')]
	data = [entry for entry in data if not entry == ['']]

	samples = []
	for i, chord_info in enumerate(data):
		start = float(chord_info[0])
		end = float(chord_info[1])
		label = chord_info[2]

		# compute number of 10ms samples per chord entry
		duration = end - start
		n_samples = round(duration/0.01)

		if (i == 0) and not (data[i][0] == '0.000'): # if the first entry in the file does not start at 0.000
			pad_n = round(float(data[i][1])/0.01)
			samples += ['N']*pad_n

		if (i > 0):
			if not data[i-1][1] == data[i][0]: 	# if end of previous entry does not match start of current entry
				pad_n = round((float(data[i][0]) - float(data[i-1][1]))/0.01) # 
				samples += ['N']*pad_n

		samples += [label]*n_samples
	
	return samples


def retrieve_f0_file_data(content, sid):
	""" I: content of melody F0 txt 
		O: list of F0 samples for the whole song (including silences) separated in beats
	"""
	# retrieve content
	data = [row.split('\t') for row in content.split('\n')]
	data = [entry for entry in data if not entry == ['']]

	# populate F0 samples list
	samples = []
	for sample in data:
		f0 = float(sample[3])
		index1 = sample[0]
		index2 = sample[1]

		# just a check since not sure what the first two columns are in the files
		if not index1 == index2:
			print("The two index values in the row do not match.")

		# append list with F0 = 0.0 Hz values when indices missing in file
		if not len(samples) == index1:
			samples += [0.0]*(int(index1) - len(samples))

		samples.append(f0)
	return samples



def retrieve_midi_file_data(content, sid):
	""" I: content of MIDI xml file
		O: list of MIDI values at every 10ms samples (including silences) separated in beats
	"""

	def get_melody_track_data(content, sid):
		# Isolate data for MELODY track
		track_pat = '(<TrackName>.*?</TrackName>(?:.|\n)*?</Track>)'
		m = re.search(track_pat, content)
		# if m == None:
		# 	track_pat = '(<TrackName>Melo</TrackName>(?:.|\n)*?</Track>)'
		# 	m = re.search(track_pat, content)

		if m == None:
			print("No MELODY track in MIDI file!", sid)
			return None


		melody_data = m.group(1)
		return melody_data

	def get_note_events_data(melody_data):
		event_pat = '(<Event>(?:.|\n)*?</Event>)'
		re_events = re.findall(event_pat, melody_data)

		# print(re_events[0])

		events = []
		for event in re_events:
			if "Note=" in event: 
				# get tick value
				tick_pat = '<Absolute>([0-9]*)</Absolute>'
				m = re.search(tick_pat, event)
				tick = m.group(1)

				# get MIDI pitch value
				pitch_pat = '<Note(.*) Channel=".*" Note="([0-9]*)".*/>'
				n = re.search(pitch_pat, event)
				switch, pitch = n.group(1), n.group(2)

				events.append((tick, switch, pitch))

		return events

	def get_end_of_track(melody_data):
		end_pat = '<Absolute>([0-9]*)</Absolute>(?: |\n)*?<EndOfTrack/>'
		m = re.search(end_pat, melody_data)
		end_of_track = m.group(1)
		return end_of_track


	def build_samples_list_by_tick(events, last):

		# check for event ascending order
		for i in range(len(events)):
			if i>0:
				if int(events[i][0]) < int(events[i-1][0]):
					print("Not in order!")

		# # check for overlaps
		# for i in range(len(events)):
		# 	if i<len(events)-1:
		# 		if (not (events[i][2]==events[i+1][2])) and (events[i][1]=="On" and events[i+1][1]=="On"):
		# 			print("Overlap!", events[i][0])

		# build samples list
		midi_samples_by_tick = [0]*(last)
		events_index = 0
		while events_index < len(events):
			if (events_index < len(events)-1):
				if events[events_index][1] == "On":
					pitch = int(events[events_index][2])
					start_tick = int(events[events_index][0])
					
					aux_index = events_index
					# end_tick = start_tick
					while (aux_index < len(events)):
						if (int(events[aux_index][2]) == pitch) and (events[aux_index][1] == "Off"):
							end_tick = int(events[aux_index][0])
							break
						aux_index += 1
					midi_samples_by_tick[start_tick:end_tick] = [pitch]*(end_tick - start_tick)

			events_index += 1

		return midi_samples_by_tick



	# retrieve xml string for melody track
	melody_data = get_melody_track_data(content, sid)
	if melody_data == None:
		return None

	# get each MIDI event
	events = get_note_events_data(melody_data)
	
	# get the tick index of the last event, i.e. length of the sample list
	last_tick = int(get_end_of_track(melody_data))

	# build sample list for every tick in original MIDI file
	midi_samples_by_tick = build_samples_list_by_tick(events, last_tick)

	# retrieve the number of ticks per beat
	# tick_per_beat = get_tick_per_beat(content) # /!\ don't need

	# build sample list at every 10msec from tick list
	# midi_samples = build_samples(midi_samples_by_tick, sid, tick_per_beat)


	return midi_samples_by_tick

# -----------------------------------------------------------------------------


def build_data_dict(sid, tpb, chord_samples, f0_samples, midi_samples):
	""" I: list of chord presence at every 10ms 
		   list of F0 presence at every 10ms
		   list of midi presence at every tick
		O: list of dict [{"chord": [], "f0": [], "midi": []}] for each non silent part in song with each inner list 10msec samples
	"""

	def ticks_in_one_bar(tpb):
		return 4*tpb

	def ten_msecs_in_one_bar(bpm):
		return (6000/bpm)*4

	# def msec_per_tick(bpm, tpb):
	# 	return 1/(bpm*tpb*60000)

	def msec_to_tick(msec, bpm, tpb):
		return round(msec*((bpm*tpb)/60000))

	def convert_tick_to_msec_sample_list(midi_samples, beat_index, bpm, tpb):
		""" I: list of midi tick samples
			   list of beat index per tick
			O: list of midi samples per 10msec samples
			   list of beat index per 10msec samples
		"""
		
		midi_samples_msec = []
		beat_index_msec = []
		msec = 0
		# print(msec_to_tick(0.01, bpm, tpb) <= len(midi_samples))
		while msec_to_tick(msec, bpm, tpb) < len(midi_samples):
			tick_index = msec_to_tick(msec, bpm, tpb)
			# print(len(midi_samples), tick_index)
			midi_samples_msec.append(midi_samples[tick_index])
			beat_index_msec.append(beat_index[tick_index])
			
			msec += 10

		return midi_samples_msec, beat_index_msec




	def concurrently_split_by_silences(f0, chord, midi, beat, bpm):
		
		# stringify f0 and chord lists to be splittable
		

		# # -----------------------------------------
		# split f0 and chord

		# Define regex patterns
		f0_pattern = "\(0\.0, '[NA-Gmajugdinsuh0-9#b\*\(\):,/]*?'\)"
		f0_pattern_rev = "\)'[A-GNmajugdinsuh0-9#b\*\(\):,/]*?' ,0\.0\("
		midi_pattern = "\(0, [0-9]*\)"
		midi_pattern_rev = "\)[0-9]* ,0\("

		# Stringify F0-chord and midi-beat
		f0_chord = '|'.join([str((f0_val, ch_val)) for (f0_val, ch_val) in zip(f0,chord)])
		midi_beat = '|'.join([str((midi_val, beat_val)) for (midi_val, beat_val) in zip(midi, beat)])

		# Strip silent events
		f0_chord = re.sub("^(?:"+f0_pattern+"\|)*", "", f0_chord)
		f0_chord = re.sub("^(?:"+f0_pattern_rev+"\|)*", "", f0_chord[::-1])[::-1]
		midi_beat = re.sub("^(?:"+midi_pattern+"\|)*", "", midi_beat)
		midi_beat = re.sub("^(?:"+midi_pattern_rev+"\|)*", "", midi_beat[::-1])[::-1]


		equalSplit = False
		silent_beat = 0
		while not equalSplit:
			silent_bar_len = round((4+silent_beat)*(6000/bpm))

			# Define splitting patterns
			f0_split_pattern = "(?:\|"+f0_pattern+"){" + str(silent_bar_len)+"}\|"
			midi_split_pattern = "(?:\|"+midi_pattern+"){"+str(silent_bar_len)+"}\|"
			
			# Split strings by silences
			l_f0 = re.split(f0_split_pattern, f0_chord)
			l_f0 = [entry for entry in l_f0 if not re.match("^"+f0_pattern+"$", entry)]
			l_midi = re.split(midi_split_pattern, midi_beat)
			l_midi = [entry for entry in l_midi if not re.match("^\(0, [0-9]*\)$", entry)]

			silent_beat += 1

			# print(len(l_f0), len(l_midi))
			if len(l_f0) == len(l_midi):
				equalSplit = True

			if silent_beat >= 16:
				print("No balanced silence splitting found!")
				break


		# Strip silences from each isolated part
		l_f0 = [re.sub("^(?:"+f0_pattern+")*\|", '', entry) for entry in l_f0]
		l_f0 = [re.sub("(?:"+f0_pattern+")*$", '', entry) for entry in l_f0]
		l_midi = [re.sub("^(?:"+midi_pattern+"\|)*", "", entry) for entry in l_midi]
		l_midi = [re.sub("(?:"+midi_pattern+")*$", "", entry) for entry in l_midi]






		# below only works if f0 and midi are split in same number of parts			
		# Turn each string of the song's separated parts to lists of tuples
		f0s = []
		chords = []
		midis = []
		beats = []
		for (f0_string, midi_string) in zip(l_f0, l_midi):
			part_f0 = []
			part_chord = []
			part_midi = []
			part_beat = []

			part_f0_chord = f0_string.split('|')
			part_midi_beat = midi_string.split('|')

			for sample_f0_chord in part_f0_chord:
				tup_f0_chord = make_tuple(sample_f0_chord)
				part_f0.append(tup_f0_chord[0])
				part_chord.append(tup_f0_chord[1])

			for sample_midi_beat in part_midi_beat:
				tup_midi_beat = make_tuple(sample_midi_beat)
				part_midi.append(tup_midi_beat[0])
				part_beat.append(tup_midi_beat[1])

			f0s.append(part_f0)
			chords.append(part_chord)
			midis.append(part_midi)
			beats.append(part_beat)
					

		return f0s, chords, midis, beats



	def finalize_data(f0s, chords, midis, beats):
		""" I: 
			O: 
			Desc: balance midis with chords and f0s with beats
		"""
		# ----------------------------
		# build chords-f0s-beats data
		
		# balance beats list length with f0-chord
		beat_len = round(6000/bpm)
		n_parts = len(f0s)

		chords_f0s_beats = []
		adjusted_beats = []
		adjusted_chords = []
		adjusted_f0s = []
		for i in range(n_parts):
			if len(f0s[i]) < len(beats[i]):
				adjusted_beats.append(beats[i][0:len(f0s[i])])
				# f0_data.append((chords[i], f0s[i], beats[i][0:len(f0s[i])]))
			elif len(f0s[i]) > len(beats[i]):
				pad_len = len(f0s[i])-len(beats[i])
				last_beat_index = beats[i][-1]
				last_beat_index_len = beats[i].count(last_beat_index)
				
				pad_start = []
				if not (last_beat_index_len >= beat_len):
					pad_start = [last_beat_index]*(beat_len - last_beat_index_len)

				pad_remain_max = ((pad_len-len(pad_start))//beat_len)+1
				pad_remain = [[j]*beat_len for j in range(last_beat_index+1, last_beat_index+1+pad_remain_max)]
				pad_remain = [y for x in pad_remain for y in x]
				pad = (pad_start+pad_remain)[0:pad_len]

				adjusted_beats.append(beats[i] + pad)
			adjusted_chords.append(chords[i])
			adjusted_f0s.append(f0s[i])


		# pad the start of each part so that the first beat index appears beat_len times
		# adjusted_chords = []
		# adjusted_f0s = []
		for i in range(n_parts):
			first_chord = adjusted_chords[i][0]
			first_beat_index = adjusted_beats[i][0]
			first_beat_index_len = adjusted_beats[i].count(first_beat_index)
			pad_len = beat_len-first_beat_index_len
			
			adjusted_beats[i] = pad_len*[first_beat_index] + adjusted_beats[i]
			adjusted_f0s[i] = pad_len*[0.0] + adjusted_f0s[i]
			# adjusted_f0s.append(pad_len*[0.0] + f0s[i])
			# adjusted_chords.append(pad_len*['N'] + chords[i])
			adjusted_chords[i] = pad_len*[first_chord] + adjusted_chords[i]

		# build the song tuple
		for i in range(n_parts):
			chords_f0s_beats.append((adjusted_chords[i], adjusted_f0s[i], adjusted_beats[i]))



		# -------------------------------
		# build chords-midi-beats data
		chords_midis_beats = []
		adjusted_chords = []
		adjusted_midis = []
		adjusted_beats = []
		for i in range(n_parts):
			if len(midis[i]) < len(chords[i]):
				adjusted_chords.append(chords[i][0:len(midis[i])])
				adjusted_midis.append(midis[i])
				adjusted_beats.append(beats[i])
			elif len(midis[i]) > len(chords[i]):
				adjusted_midis.append(midis[i][0:len(chords[i])])
				adjusted_beats.append(beats[i][0:len(chords[i])])
				adjusted_chords.append(chords[i])

		# 
		for i in range(n_parts):
			# find the value to fill with and other numbers
			first_chord = adjusted_chords[i][0]
			first_beat_index = adjusted_beats[i][0]
			first_beat_index_len = adjusted_beats[i].count(first_beat_index)
			pad_len = beat_len - first_beat_index_len

			# fill the beginning of each part with those values
			adjusted_midis[i] = pad_len*[0] + adjusted_midis[i]
			adjusted_beats[i] = pad_len*[first_beat_index] + adjusted_beats[i]
			# adjusted_chords[i] = pad_len*['N'] + adjusted_chords[i]
			adjusted_chords[i] = pad_len*[first_chord] + adjusted_chords[i]
		

		return chords_f0s_beats, chords_midis_beats


	def create_midi_samples_beat_index_pair(midi_samples, tpb):
		""" I: list of midi samples per tick
			   int of ticks per beat
			O: list of int indices of beat number
		"""
		pad = [0]*(tpb-len(midi_samples)%tpb)
		samples = list(midi_samples+pad)

		n_beats = len(samples)//tpb
		# print(n_beats)

		beat_index = []
		for i in range(n_beats):
			beat_index += [i]*tpb
		return samples, beat_index

	def balance_f0_chord_lists(f0, chord):
		if len(f0)>len(chord):
			difference = len(f0)-len(chord)
			chord += ['N']*difference
		elif len(f0)<len(chord):
			difference = len(chord) - len(f0)
			f0 += [0.0]*difference
		else:
			pass
		return f0, chord 



	# Take a deep breath. GO GO GO !!
	# You're almost there. :)

	bpm = get_bpm(sid)
	# create beat index - midi samples list pair
	midi_samples_tick, beat_index_tick = create_midi_samples_beat_index_pair(midi_samples, tpb)

	# convert midi_samples and beat indices to 10 msec samples	
	midi_samples_msec, beat_index_msec = convert_tick_to_msec_sample_list(midi_samples_tick, beat_index_tick, bpm, tpb)

	# balance length of f0 and chord lists
	f0_samples, chord_samples = balance_f0_chord_lists(f0_samples, chord_samples)

	# split the song in meaningful non-silent parts
	f0s, chords, midis, beats = concurrently_split_by_silences(f0_samples, chord_samples, midi_samples_msec, beat_index_msec, bpm)

	# build the two datasets
	chords_f0s_beats, chords_midis_beats = finalize_data(f0s, chords, midis, beats)

	return chords_f0s_beats, chords_midis_beats





if __name__ == "__main__":
	""" Output:
		- MIDI-chords pickled dictionary of each song
		- F0-chords pickled dictionary of each song
		Each set of list is in 10 msec samples.
		MIDI, F0 and chords sample lists all have the same length.
	"""

	rootdir = "/Users/Maxime/Research/Workbench/Repositories/singing-voice-harmonization/" 

	chords_dir = rootdir + "data/chord/AIST.RWC-MDB-P-2001.CHORD/RWC_Pop_Chords/"
	f0_dir = rootdir + "data/f0/AIST.RWC-MDB-P-2001.MELODY/"	
	midi_dir = rootdir + "data/midi/MIDI.MELODY.XML/"


	# Retrieve raw Chords data (10 msec samples)
	chords_dict = {}
	for filename in os.listdir(chords_dir):
		if filename.endswith(".lab"):
			chords_file_content = get_file_content(chords_dir+filename)
			song_id = get_chords_file_song_id(filename)
			chords_dict[song_id] = retrieve_chords_file_data(chords_file_content, song_id)		

	# Retrieve raw F0 data (10 msec samples)
	f0_dict = {}
	for filename in os.listdir(f0_dir):
		if filename.endswith("MELODY.TXT"):
			f0_file_content = get_file_content(f0_dir+filename)
			song_id = get_f0_file_song_id(filename)
			f0_dict[song_id] = retrieve_f0_file_data(f0_file_content, song_id)

	# Retrieve raw MIDI data (ticks)
	midi_dict = {}
	for filename in os.listdir(midi_dir):
		if filename.endswith(".xml"):
			midi_file_content = get_file_content(midi_dir+filename)
			song_id = get_midi_file_song_id(filename)
			midi_dict[song_id] = retrieve_midi_file_data(midi_file_content, song_id)	


	# Concurrently isolate meaningful melody parts (separated by more than ~2-5sec of silences depending on the bpm -> e.g. more than 1 bar)

	# get TicksPerBeat	
	tpb = []
	for filename in os.listdir(midi_dir):
		if filename.endswith(".xml"):
			midi_file_content = get_file_content(midi_dir+filename)
			tpb.append(get_tick_per_beat(midi_file_content))

	if len(set(tpb)) > 1:
		print("Inconsistent TicksPerBeat across MIDI xml files!")
	tpb = list(set(tpb))[0]



	chords_f0s_beats = {}
	chords_midis_beats = {}
	blacklist = [4, 28, 63, 95]	
	for i in range(1, 101):
		if i not in blacklist:
			index = "{:>3}".format(i).replace(' ', '0')
			if index in midi_dict:
				print(index)
				song_chords_f0s_beats, song_chords_midis_beats = build_data_dict(index, tpb, chords_dict[index], f0_dict[index], midi_dict[index])
				
				f0s_song_list = []
				midis_song_list = []
				for j in range(len(song_chords_f0s_beats)):
					f0s_part_dict = {"chords": song_chords_f0s_beats[j][0], "f0s": song_chords_f0s_beats[j][1], "beats": song_chords_f0s_beats[j][2]}
					midis_part_dict = {"chords": song_chords_midis_beats[j][0], "midis": song_chords_midis_beats[j][1], "beats": song_chords_midis_beats[j][2]}
					f0s_song_list.append(f0s_part_dict)
					midis_song_list.append(midis_part_dict)
					

				chords_f0s_beats[index] = f0s_song_list
				chords_midis_beats[index] = midis_song_list



	pickle.dump(chords_f0s_beats, open("../data/chords-f0s-beats.pkl", "wb"))
	pickle.dump(chords_midis_beats, open("../data/chords-midis-beats.pkl", "wb"))

