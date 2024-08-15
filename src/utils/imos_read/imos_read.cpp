#include <stdio.h>
#include <stdint.h>
#include <cstdlib>
#include <sndfile.h>
#include <cstring>
#include <malloc.h>

#include "imos_read.h"

void swapBytes(U16* data, const size_t count)
{
    U16 value;
    for (size_t i = 0; i < count; i++)
    {
        value = data[i];
        data[i] = (value >> 8) | (value << 8);
    }
}

void convertU16ToI16(const U16* input, I16* output, const size_t count)
{
    for (size_t i = 0; i < count; i++)
    {
        // Convert U16 to I16 by subtracting the midpoint
        output[i] = (I16)((I32)(input[i]) - (1 << (16 - 1)));
    }
}

/*
    Read (only) the header IMOS .dat sound record file

    Returns number of individual sound samples as calculated from the header
*/
int imos_rawDatReadHeader(const char *fileName,
    int *numHeaderLines,
    unsigned int *samplesInFile,
    char** header)
{
    FILE *file = fopen(fileName, "r");
    if (file == NULL) {
        perror("Error opening file");
        return -1;
    }

    /* read header lines */
    int i;
    for (i = 0; i < IMOS_NUM_HEADER_LINES; i++) \
    {
        if(fgets(header[i], IMOS_HEADER_LINE_SIZE_MAX, file) == NULL)
        {   
            fclose(file);
            perror("Error: Unexpected error or end of file while reading header");
            return -1;
        }
    }
    fclose(file);
    *numHeaderLines = i;
    
    /* parse header - only minimal */
    unsigned int sampleRate = 0;
    unsigned int durationSeconds = 0;

    sscanf(header[2], "Sample Rate %d Duration %d", &sampleRate, &durationSeconds);
    
    *samplesInFile = sampleRate * durationSeconds;

    printf("*samplesInFile = %d\n", *samplesInFile);

    return((int)(*samplesInFile));
}

/*
    Read IMOS .dat sound record file

    return 
*/
int imos_rawDatReadAll(const char* fileName,
    int *numHeaderLines,
    int *numFooterLines,
    unsigned int *samplesInFile,
    char** header,
    char** footer,
    U16* data)
{
    FILE *file = fopen(fileName, "r");
    if (file == NULL) {
        perror("Error opening file");
        return 1;
    }

    /* read header lines */
    int i;
    for (i = 0; i < IMOS_NUM_HEADER_LINES; i++) \
    {
        if(fgets(header[i], IMOS_HEADER_LINE_SIZE_MAX, file) == NULL)
        {   
            perror("Error: Unexpected error or end of file while reading header");
            return 1;
        }
    }
    *numHeaderLines = i;
    
    /* parse header - only minimal */
    unsigned int sampleRate = 0;
    unsigned int durationSeconds = 0;

    sscanf(header[2], "Sample Rate %d Duration %d", &sampleRate, &durationSeconds);
    
    *samplesInFile = sampleRate * durationSeconds;

    printf("samplesInFile = %d\n", *samplesInFile);

    size_t samplesRead = fread(data, sizeof(U16), *samplesInFile, file);
    printf("samplesRead = %lu\n", samplesRead);
    if(samplesRead < (size_t)(*samplesInFile)) 
    {
        perror("Error: file contains less sound data than expected from header");
        return 1;
    }

    /* Raw DAT files are uint16_t big-endian, need to correct for that */
    swapBytes(data, samplesRead);

    /* read footer / marker lines */

    i = 0;
    for (i = 0; i < IMOS_NUM_MARKER_LINES_MAX; i++) 
    {
        if(fgets(footer[i], IMOS_HEADER_LINE_SIZE_MAX, file) == NULL)
        {
            break;
        }
    }
    if(i < IMOS_NUM_MARKER_LINES_MIN)
    {
        perror("Error: Unexpected error or end of file while reading footer");
        return 1;
    }
    *numFooterLines = i;

    return(0);
}

/*
    Read (and drop) the header IMOS .dat sound record file
    then read the binary sound data

    Returns number of individual sound samples as read from the file
        or -1 in case of error
*/
int imos_rawDatRead(const char* fileName,
    unsigned int samplesHeader,
    char** header,
    U16* data)
{
    FILE *file = fopen(fileName, "r");
    if (file == NULL) {
        perror("Error opening file");
        return 1;
    }

    /* read header lines to get to the binary sound data*/
    int i;
    for (i = 0; i < IMOS_NUM_HEADER_LINES; i++) \
    {
        if(fgets(header[i], IMOS_HEADER_LINE_SIZE_MAX, file) == NULL)
        {   
            fclose(file);
            perror("Error: Unexpected error or end of file while reading header");
            return -1;
        }
    }
    
    size_t samplesRead = fread(data, sizeof(U16), samplesHeader, file);
    fclose(file);

    printf("samplesRead = %d\n", (int)samplesRead);
    if(samplesRead < samplesHeader) 
    {
        perror("Error: file contains less sound data than expected from header");
        return -1;
    }

    /* Raw DAT files are uint16_t big-endian, need to correct for that */
    swapBytes(data, samplesRead);

    return((int)samplesRead);
}

int writeWAV(const char* fileName, 
    unsigned int sampleRate,
    unsigned int timeSeconds,
    I16* data)
{   
    SNDFILE	*file ;
	SF_INFO	sfinfo ;
    memset (&sfinfo, 0, sizeof (sfinfo));

    sfinfo.samplerate	= sampleRate;
	sfinfo.frames		= (timeSeconds * sampleRate);
	sfinfo.channels		= 1;
	sfinfo.format		= (SF_FORMAT_WAV | SF_FORMAT_PCM_16);
    
    printf("in write, before open    ");
    printf("sfinfo.frames = %d\n", (int)(sfinfo.frames));

    if (! (file = sf_open(fileName, SFM_WRITE, &sfinfo)))
	{	printf ("Error : Not able to open output file %s.\n", fileName) ;
		return 1 ;
	}

    printf("in write, after open    ");
    
    printf("sfinfo.samplerate = %d\n", (int)(sfinfo.samplerate));
    printf("sfinfo.frames = %d\n", (int)(sfinfo.frames));
    printf("sfinfo.channels = %d\n", (int)(sfinfo.channels));
    printf("sfinfo.channels * sfinfo.frames = %d\n", (int)(sfinfo.channels * sfinfo.frames));
    printf("sampleRate = %d   durationSeconds = %d\n", sampleRate, timeSeconds);


    printf("in write, fixed before write_short    ");
    sfinfo.frames		= (timeSeconds * sampleRate);
	printf("sfinfo.frames = %d\n", (int)(sfinfo.frames));
    printf("sfinfo.channels * sfinfo.frames = %d\n", (int)(sfinfo.channels * sfinfo.frames));    

    sf_count_t wrFrames = sf_write_short(file, (short*)data, (sf_count_t)(sfinfo.channels * sfinfo.frames));
    if ( wrFrames != (sfinfo.channels * sfinfo.frames))
		{
            printf("wrFrames = %d\n", (int)wrFrames);
            puts(sf_strerror (file));
        }

	sf_close(file);
	
    printf("closed    sizeof(short)=%d\n", (int)sizeof(short));
	return 0 ;
}

int main(int argc, const char ** argv)
{
    int numHeaderLines = 0;
    int numFooterLines = 0;
    int numSoundSamples = 0;  
    char* headerLines[5];
    char* footerLines[6];
    int retval = -1; /* assume failed */
    int i;

    for(i=0; i<5; i++)
    {
        headerLines[i] = (char*)malloc(IMOS_HEADER_LINE_SIZE_MAX * sizeof(char));
    }
    for(i=0; i<6; i++)
    {
        footerLines[i] = (char*)malloc(IMOS_HEADER_LINE_SIZE_MAX *sizeof(char));
    }
    
    unsigned int numSamplesHeader = 0;
    /* /home/martin/src/CIDS/ADACS2/IMOS/NDRI-IMOS/src/utils/imos_read/595A2725.DAT */

    // if(imos_rawDatReadHeader("/home/martin/src/CIDS/ADACS2/IMOS/NDRI-IMOS/src/utils/imos_read/595A2725.DAT",
    if(imos_rawDatReadHeader("54842511.DAT",
        &numHeaderLines, &numSamplesHeader, headerLines) < 0)
    {
        printf("ERROR: imos_rawDatReadHeader() failed!\n");
        exit(1);
    }

    U16* rawSound = (U16*)malloc(numSamplesHeader * sizeof(U16));
    size_t allSize = malloc_usable_size((void*)rawSound);
    printf("allocated size = %d\n", (int)allSize);

    numSoundSamples = imos_rawDatRead("54842511.DAT", numSamplesHeader, headerLines, rawSound);
    if(numSoundSamples == numSamplesHeader)
    {
        retval = 0;
    }

    I16* sound = (I16*)malloc(numSamplesHeader * sizeof(I16));
    
    /* convert to signed integer */
    convertU16ToI16(rawSound, sound, numSoundSamples);
    free(rawSound);

    unsigned int sampleRate = 0;
    unsigned int durationSeconds = 0;

    sscanf(headerLines[2], "Sample Rate %d Duration %d", &sampleRate, &durationSeconds);
    printf("call write: sampleRate = %d   durationSeconds = %d\n", sampleRate, durationSeconds);

    writeWAV("54842511.WAV",
        sampleRate,
        durationSeconds,
        sound);
    free(sound);

    exit(retval);
}