##### Adlib Instrument Bank file tool

Extracts, updates and removes `*.wem` audio files.

examples:
* `bnktool.py sb.bnk -l`
* `bnktool.py AMB_GenericVillage.bnk -x`
* `bnktool.py AMB_GenericVillage.bnk -u [list.txt]`

When audio samples are modified, the Bank file is saved and a backup is made with incremental extension `.000`, `.001` and so on. 

The makefile is an example to remove unwanted audio files by replacing their content with zero-length audio data.
* copy the `foo.bnk` file in a directory 
* put the names of the audio samples to remove in `foo.txt` (same name, `.txt` extension)
* `make`

To listen to extracted samples, you must convert the `.wem` files to `.wav` or `.ogg` files, this is not supported by this tool.
