#! /usr/bin/env python
#'''
###################################################################################
#                                                                                 #
#            Author:   Yun-Meng Cao                                               #
#            Email :   ymcmrs@gmail.com                                           #
#            Date  :   March, 2017                                                #
#                                                                                 #
#          Geocoding for Sentinel-1                                               #
#                                                                                 #
###################################################################################
#'''
import numpy as np
import os
import sys  
import subprocess
import getopt
import time
import glob

def check_variable_name(path):
    s=path.split("/")[0]
    if len(s)>0 and s[0]=="$":
        p0=os.getenv(s[1:])
        path=path.replace(path.split("/")[0],p0)
    return path

def read_template(File, delimiter='='):
    '''Reads the template file into a python dictionary structure.
    Input : string, full path to the template file
    Output: dictionary, pysar template content
    Example:
        tmpl = read_template(KyushuT424F610_640AlosA.template)
        tmpl = read_template(R1_54014_ST5_L0_F898.000.pi, ':')
    '''
    template_dict = {}
    for line in open(File):
        line = line.strip()
        c = [i.strip() for i in line.split(delimiter, 1)]  #split on the 1st occurrence of delimiter
        if len(c) < 2 or line.startswith('%') or line.startswith('#'):
            next #ignore commented lines or those without variables
        else:
            atrName  = c[0]
            atrValue = str.replace(c[1],'\n','').split("#")[0].strip()
            atrValue = check_variable_name(atrValue)
            template_dict[atrName] = atrValue
    return template_dict

def ras2jpg(input, strTitle):
    call_str = "convert " + input + ".ras " + input + ".jpg"
    os.system(call_str)
    call_str = "convert " + input + ".jpg -resize 250 " + input + ".thumb.jpg"
    os.system(call_str)
    call_str = "convert " + input + ".jpg -resize 500 " + input + ".bthumb.jpg"
    os.system(call_str)
    call_str = "$INT_SCR/addtitle2jpg.pl " + input + ".thumb.jpg 14 " + strTitle
    os.system(call_str)
    call_str = "$INT_SCR/addtitle2jpg.pl " + input + ".bthumb.jpg 24 " + strTitle
    os.system(call_str)

def UseGamma(inFile, task, keyword):
    if task == "read":
        f = open(inFile, "r")
        while 1:
            line = f.readline()
            if not line: break
            if line.count(keyword) == 1:
                strtemp = line.split(":")
                value = strtemp[1].strip()
                return value
        print "Keyword " + keyword + " doesn't exist in " + inFile
        f.close()
        
def geocode(inFile, outFile, UTMTORDC, nWidth, nWidthUTMDEM, nLineUTMDEM):
    if ( inFile.rsplit('.')[len(inFile.rsplit('.'))-1] == 'int' or inFile.rsplit('.')[len(inFile.rsplit('.'))-1] == 'diff' ):
        call_str = '$GAMMA_BIN/geocode_back ' + inFile + ' ' + nWidth + ' ' + UTMTORDC + ' ' + outFile + ' ' + nWidthUTMDEM + ' ' + nLineUTMDEM + ' 0 1'
    else:
        call_str = '$GAMMA_BIN/geocode_back ' + inFile + ' ' + nWidth + ' ' + UTMTORDC + ' ' + outFile + ' ' + nWidthUTMDEM + ' ' + nLineUTMDEM + ' 0 0'
    os.system(call_str)
    
def createBlankFile(strFile):
    f = open(strFile,'w')
    for i in range (10):
        f.write('\n')
    f.close()    
    
       

def usage():
    print '''
******************************************************************************************************
 
              Generating the differential interferograms for Sentinel-1A/B

   usage:
   
            DiffPhase_Sen_Gamma.py igramDir
      
      e.g.  DiffPhase_Sen_Gamma.py IFG_PacayaT163S1A_131021-131101_0011_-0007
      e.g.  DiffPhase_Sen_Gamma.py MAI_PacayaT163S1A_131021-131101_0011_-0007          
      e.g.  DiffPhase_Sen_Gamma.py RSI_PacayaT163S1A_131021-131101_0011_-0007            
*******************************************************************************************************
    '''   
    
def main(argv):
    
    if len(sys.argv)==2:
        if argv[0] in ['-h','--help']: usage(); sys.exit(1)
        else: igramDir=sys.argv[1]        
    else:
        usage();sys.exit(1)
       
    INF = igramDir.split('_')[0]
    projectName = igramDir.split('_')[1]
    IFGPair = igramDir.split(projectName+'_')[1].split('_')[0]
    Mdate = IFGPair.split('-')[0]
    Sdate = IFGPair.split('-')[1]
    
    scratchDir = os.getenv('SCRATCHDIR')
    templateDir = os.getenv('TEMPLATEDIR')
    templateFile = templateDir + "/" + projectName + ".template"
    
    processDir = scratchDir + '/' + projectName + "/PROCESS"
    slcDir     = scratchDir + '/' + projectName + "/SLC"
    workDir    = processDir + '/' + igramDir   
    geoDir     = processDir + "/GEO"
    simDir = scratchDir + '/' + projectName + "/PROCESS" + "/SIM" 
    simDir = simDir + '/sim_' + Mdate + '-' + Sdate


    if not os.path.isdir(geoDir):
        call_str='mkdir ' + geoDir
        os.system(call_str)

    templateContents=read_template(templateFile)
    rlks = templateContents['Range_Looks']
    azlks = templateContents['Azimuth_Looks']

    if 'Igram_Cor_Rwin' in templateContents: rWinCor = templateContents['Igram_Cor_Rwin']
    else: rWinCor = '5'
    if 'Igram_Cor_Awin' in templateContents: aWinCor = templateContents['Igram_Cor_Awin']
    else: aWinCor = '5'

    if 'Unwrap_Flattening'          in templateContents: flatteningUnwrap = templateContents['Unwrap_Flattening']                
    else: flatteningUnwrap = 'N'

    if 'UnwrappedThreshold' in templateContents: unwrappedThreshold = templateContents['UnwrappedThreshold']
    else: unwrappedThreshold = '0.3'
    if 'Unwrap_patr' in templateContents: unwrappatrDiff = templateContents['Unwrap_patr']
    else: unwrappatrDiff = '1'
    if 'Unwrap_pataz' in templateContents: unwrappatazDiff = templateContents['Unwrap_pataz']
    else: unwrappatazDiff = '1'
        
    if 'Start_Swath' in templateContents: SW = templateContents['Start_Swath']
    else: SW = '1'    
    if 'End_Swath' in templateContents: EW = templateContents['End_Swath']
    else: EW = '3' 
    if 'Start_Burst' in templateContents: SB = templateContents['Start_Burst']
    else: SB = '1'            
        
#  Definition of file
    MslcDir     = slcDir  + '/' + Mdate
    SslcDir     = slcDir  + '/' + Sdate

    MslcTOP1     = MslcDir + '/' + Mdate + '.IW1.slc.TOPS_par'   # bursts number in all of TOPS are same ? If not, should modify
    SslcTOP1     = SslcDir + '/' + Sdate + '.IW1.slc.TOPS_par'

    NB_master = UseGamma(MslcTOP1 , 'read', 'number_of_bursts:')
    NB_slave = UseGamma(SslcTOP1 , 'read', 'number_of_bursts:')    
    
    if 'End_Burst' in templateContents: EB = templateContents['End_Burst']
    else: EB = str(min(int(NB_master),int(NB_slave)))    # using the minmun number as the end of the burst number
    
    MSLC_tab     = MslcDir + '/SLC_Tab2_' + SW + EW + '_' + SB + EB 
    SSLC_tab     = SslcDir + '/SLC_Tab2_' + SW + EW + '_' + SB + EB 
    
    MamprlksImg = MslcDir + '/' + Mdate + '.' + SW + EW + '_' + SB + EB +'_'+rlks +'rlks.amp'
    MamprlksPar = MslcDir + '/' + Mdate + '.' + SW + EW + '_' + SB + EB +'_'+rlks +'rlks.amp.par'

    SamprlksImg = SslcDir + '/' + Sdate + '.' + SW + EW + '_' + SB + EB +'_'+rlks +'rlks.amp'
    SamprlksPar = SslcDir + '/' + Sdate + '.' + SW + EW + '_' + SB + EB +'_'+rlks +'rlks.amp.par'

    UTMDEMpar   = simDir + '/sim_' + Mdate + '-' + Sdate + '_'+ rlks + 'rlks.utm.dem.par'
    UTMDEM      = simDir + '/sim_' + Mdate + '-' + Sdate + '_'+ rlks + 'rlks.utm.dem'
    UTM2RDC     = simDir + '/sim_' + Mdate + '-' + Sdate + '_'+ rlks + 'rlks.utm_to_rdc'
    SIMSARUTM   = simDir + '/sim_' + Mdate + '-' + Sdate + '_'+ rlks + 'rlks.sim_sar_utm'
    PIX         = simDir + '/sim_' + Mdate + '-' + Sdate + '_'+ rlks + 'rlks.pix'
    LSMAP       = simDir + '/sim_' + Mdate + '-' + Sdate + '_'+ rlks + 'rlks.ls_map'
    SIMSARRDC   = simDir + '/sim_' + Mdate + '-' + Sdate + '_'+ rlks + 'rlks.sim_sar_rdc'
    SIMDIFFpar  = simDir + '/sim_' + Mdate + '-' + Sdate + '_'+ rlks + 'rlks.diff_par'
    SIMOFFS     = simDir + '/sim_' + Mdate + '-' + Sdate + '_'+ rlks + 'rlks.offs'
    SIMSNR      = simDir + '/sim_' + Mdate + '-' + Sdate + '_'+ rlks + 'rlks.snr'
    SIMOFFSET   = simDir + '/sim_' + Mdate + '-' + Sdate + '_'+ rlks + 'rlks.offset'
    SIMCOFF     = simDir + '/sim_' + Mdate + '-' + Sdate + '_'+ rlks + 'rlks.coff'
    SIMCOFFSETS = simDir + '/sim_' + Mdate + '-' + Sdate + '_'+ rlks + 'rlks.coffsets'
    UTMTORDC    = simDir + '/sim_' + Mdate + '-' + Sdate + '_'+ rlks + 'rlks.UTM_TO_RDC'
    HGTSIM      = simDir + '/sim_' + Mdate + '-' + Sdate + '_'+ rlks + 'rlks.rdc.dem'
    SIMUNW      = simDir + '/sim_' + Mdate + '-' + Sdate + '_'+ rlks + 'rlks.sim_unw'


    RSLC_tab = workDir + '/RSLC_tab' +  SW + EW + '_' + SB + EB
    DIFF0     = workDir + '/' + Mdate + '_' + Sdate +'.diff'
    DIFFlks     = workDir + '/' + Mdate + '-' + Sdate + '_' + rlks + 'rlks.diff'
    DIFFFILTlks = workDir + '/' + Mdate + '-' + Sdate + '_' + rlks + 'rlks.filt.diff'
    UNWlks  =  workDir + '/' + Mdate + '-' + Sdate + '_' + rlks + 'rlks.unw'
    UNWINTERPlks = workDir + '/' + Mdate + '-' + Sdate + '_' + rlks + 'rlks.unw_interp'
    DIFFpar = workDir + '/' + Mdate + '-' + Sdate +'.diff_par'
    QUADFIT = workDir + '/' + Mdate + '-' + Sdate +'.quad_fit'

    CORDIFFFILTlks = workDir + '/' + Mdate + '-' + Sdate + '_' + rlks + 'rlks.filt_diff.cor'
    MASKTHINDIFFlks  = CORDIFFFILTlks + 'maskt.bmp'


    GEOPWR = geoDir + '/geo_'+ Mdate + '.' + SW + EW + '_' + SB + EB +'_'+rlks +'rlks.amp'
    GEODIFFlks = geoDir + '/geo_' + Mdate + '-' + Sdate + '_' + rlks + 'rlks.diff'
    GEODIFFFILTlks = geoDir + '/geo_' + Mdate + '-' + Sdate + '_' + rlks + 'rlks.filt.diff'
    GEOUNW = geoDir + '/geo_' + Mdate + '-' + Sdate + '_' + rlks + 'rlks.unw'
    GEOQUADUNW = geoDir + '/geo_' + Mdate + '-' + Sdate + '_' + rlks + 'rlks.quad_fit.unw'
    GEOCOR = geoDir + '/geo_' + Mdate + '-' + Sdate + '_' + rlks + 'rlks.filt_diff.cor'


    QUADUNWlks   = UNWlks.replace('.unw','.quad_fit.unw')


    nWidth = UseGamma(MamprlksPar, 'read', 'range_samples')
    nWidthUTMDEM = UseGamma(UTMDEMpar, 'read', 'width')
    nLineUTMDEM = UseGamma(UTMDEMpar, 'read', 'nlines')


#    if flatteningIgram == 'fft':
#      FLTlks = FLTFFTlks 

#    FLTFILTlks = FLTlks.replace('flat_', 'filt_')

    geocode(MamprlksImg, GEOPWR, UTMTORDC, nWidth, nWidthUTMDEM, nLineUTMDEM)
    geocode(CORDIFFFILTlks, GEOCOR, UTMTORDC, nWidth, nWidthUTMDEM, nLineUTMDEM)
    geocode(DIFFlks, GEODIFFlks, UTMTORDC, nWidth, nWidthUTMDEM, nLineUTMDEM)
    geocode(DIFFFILTlks, GEODIFFFILTlks, UTMTORDC, nWidth, nWidthUTMDEM, nLineUTMDEM)
    geocode(UNWlks, GEOUNW, UTMTORDC, nWidth, nWidthUTMDEM, nLineUTMDEM)


    if flatteningUnwrap == 'Y':
        geocode(QUADUNWlks, GEOQUADUNW, UTMTORDC, nWidth, nWidthUTMDEM, nLineUTMDEM)
        
        call_str = '$GAMMA_BIN/rasrmg ' + GEOQUADUNW + ' ' + GEOPWR + ' ' + nWidthUTMDEM + ' - - - - - - - - - - ' 
        os.system(call_str)
        ras2jpg(GEOQUADUNW, GEOQUADUNW) 
    
    call_str = '$GAMMA_BIN/raspwr ' + GEOPWR + ' ' + nWidthUTMDEM + ' - - - - - - - '
    os.system(call_str)
    ras2jpg(GEOPWR, GEOPWR)

    call_str = '$GAMMA_BIN/rascc ' + GEOCOR + ' ' + GEOPWR + ' ' + nWidthUTMDEM + ' - - - - - - - - - -' 
    os.system(call_str)
    ras2jpg(GEOCOR, GEOCOR) 

    call_str = '$GAMMA_BIN/rasmph_pwr ' + GEODIFFlks + ' ' + GEOPWR + ' ' + nWidthUTMDEM + ' - - - - - 2.0 0.3 - ' 
    os.system(call_str)
    ras2jpg(GEODIFFlks, GEODIFFlks)

    call_str = '$GAMMA_BIN/rasmph_pwr ' + GEODIFFFILTlks + ' ' + GEOPWR + ' ' + nWidthUTMDEM + ' - - - - - 2.0 0.3 - ' 
    os.system(call_str)
    ras2jpg(GEODIFFFILTlks, GEODIFFFILTlks)

    call_str = '$GAMMA_BIN/rasrmg ' + GEOUNW + ' ' + GEOPWR + ' ' + nWidthUTMDEM + ' - - - - - - - - - - ' 
    os.system(call_str)
    ras2jpg(GEOUNW, GEOUNW) 






    print "Geocoding for S1 interferogram is done !"
    sys.exit(1)

if __name__ == '__main__':
    main(sys.argv[:])
