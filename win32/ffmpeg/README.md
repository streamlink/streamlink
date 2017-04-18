The `ffmpeg.exe` binary was compiled using https://github.com/rdp/ffmpeg-windows-build-helpers with the following command line options
```
./cross_compile_ffmpeg.sh --ffmpeg-git-checkout-version=n3.2.4 --build-intel-qsv=n
```
Then selecting to only use the free license libraries and only build Win32 MinGW-w64. `--build-intel-qsv=n` enabled Windows XP support.

The resulting `ffmpeg.exe` binary was tested on:
 * Windows XP Professional SP3
 * Windows Vista Enterprise SP2
 * Windows 7 Enterprise SP1
 * Windows 10 Home 1607
 
Compilation date: 2017-03-08
