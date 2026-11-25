# Pin assignment check: synthesise and place the test design with the OSS CAD Suite
# (yosys, nextpnr-ice40) on the iCE40UP5K-SG48 with hardware/fpga-pins.csv.

all: top.asc

top.pcf: ../../hardware/fpga-pins.csv gen_pcf.py
	python gen_pcf.py $< > $@

top.json: top.v
	yosys -q -p "synth_ice40 -top top -json $@" $<

top.asc: top.json top.pcf clocks.py
	nextpnr-ice40 --up5k --package sg48 --json top.json --pcf top.pcf \
		--pre-pack clocks.py --asc $@ --report report.json --log nextpnr.log

clean:
	rm -f top.json top.asc report.json nextpnr.log

.PHONY: all clean
