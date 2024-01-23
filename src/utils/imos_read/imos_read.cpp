#include <stdio.h>
#include <stdint.h>
#include <cstdlib>

#include "imos_read.h"

/*
    Read IMOS .dat sound record file

    allocates the sound data array
*/
int imos_rawDatRead(const char* fileName,
    int& numHeaderLines,
    int& numFooterLines,
    unsigned int& samplesInFile,
    char** header,
    char** footer,
    I16* data)
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
    numHeaderLines = i;
    
    /* parse header - only minimal */
    unsigned int sampleRate = 0;
    unsigned int durationSeconds = 0;

    sscanf(header[2], "Sample Rate %d Duration %d", &sampleRate, &durationSeconds);
    printf("sampleRate = %d   durationSeconds = %d\n", sampleRate, durationSeconds);

    samplesInFile = sampleRate * durationSeconds;
    data = (int16_t *)malloc(samplesInFile * sizeof(int16_t));
    size_t samplesRead = fread(data, sizeof(U16), samplesInFile, file);
    printf("samplesRead = %d\n", (int)samplesRead);
    if(samplesRead < samplesInFile) 
    {
        perror("Error: file contains less sound data than expected from header");
        return 1;
    }

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
    numFooterLines = i;

    return(0);
}

int main(int argc, const char ** argv)
{
    int numHeaderLines = 0;
    int numFooterLines = 0;
    unsigned int numSoundSamples = 0;  
    char* headerLines[5];
    char* footerLines[6];
    int i;
    for(i=0; i<5; i++)
    {
        headerLines[i] = (char*)malloc(IMOS_HEADER_LINE_SIZE_MAX * sizeof(char));
    }
    for(i=0; i<6; i++)
    {
        footerLines[i] = (char*)malloc(IMOS_HEADER_LINE_SIZE_MAX *sizeof(char));
    }

    I16* sound;

    int retval = imos_rawDatRead( 
        "595A2725.DAT",
        numHeaderLines,
        numFooterLines,
        numSoundSamples,
        headerLines, footerLines,
        sound);

    exit(retval);
}