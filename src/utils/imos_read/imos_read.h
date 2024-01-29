#ifndef __IMOS_READ_H__
#define __IMOS_READ_H__

/*
    Read IMOS raw dat sound files
    Inspired by:
    https://github.com/aodn/data-services/blob/master/ANMN/acoustic/NL_load_logger_data_new.m
*/

#include "types.h"

#define IMOS_NUM_HEADER_LINES         5	 // Number of header lines
#define IMOS_NUM_MARKER_LINES_MAX     6  // Number of marker lines (maximum)
                                         // there are files with only 4 marker lines
#define IMOS_NUM_MARKER_LINES_MIN     4  // Number of marker lines (maximum)
//#define IMOS_MARKER_FOOTER_LENGTH    14  // Number of characters in footer (marker)
                                         // this is wrong, the lines are longer

#define IMOS_HEADER_LINE_SIZE_MAX 64     // max size of IMOS header/footer line (better be safe)

/* Header example
Record Header-       E24 set# 3444
Schedule 1 2017/07/03 11:15:01 - 34282
Sample Rate 06000 Duration 0000000300
Filter 0 C0=1 C1=0 LF=008 HF=02800 PG=010 G=001
Filter 1 C2=0 C3=0 LF=008 HF=05000 PG=001 G=001

Record Header-     SNR041_SET#3445
Schedule 1 2016/12/22 09:15:01 - 43792
Sample Rate 06000 Duration 0000000300
Filter 0 C0=1 C1=0 LF=008 HF=02800 PG=010 G=001
Filter 1 C2=0 C3=0 LF=008 HF=01800 PG=001 G=010

Record Header-      Silicon_IMOS_1
Schedule 1 2008/03/02 07:15:01 - 23136
Sample Rate 06000 Duration 0000000200
Filter 0 C0=1 C1=0 LF=008 HF=02800 PG=010 G=001
Filter 1 C2=0 C3=0 LF=008 HF=04000 PG=010 G=001
*/

/* Footer/Marker example
Record Marker
First Data-2017/07/03 11:15:01 - 35378
Finalised -2017/07/03 11:20:08 - 54240
Data Validity - data is ok 
Data to RAM = 0
Data block size = 0065536

Record Marker
First Data-2016/12/22 09:15:01 - 44876
Finalised -2016/12/22 09:20:08 - 63282
Data Validity - data is ok 

Record Marker
First Data-2008/03/02 07:15:01 - 24218
Finalised -2008/03/02 07:18:26 - 21256
Data Validity - data is ok 
*/

/* typedef struct imos_datHeader 
*/

int imos_rawDatReadAll(const char* fileName,
                    int& headerLines,
                    int& footerLines,
                    unsigned int& samplesInFile,
                    char** header,
                    char** footer,
                    I16* data);

int writeWAV(const char* fileName,
    unsigned int sampleRate,
    unsigned int timeSeconds,
    I16* data);

#endif // IMOS_READ_H
