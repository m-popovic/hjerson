#!/usr/bin/env python
# -*- coding: utf8 -*-

# Copyright 2018 Maja Popović
# The program is distributed under the terms 
# of the GNU General Public Licence (GPL)

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>. 


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Publications of results obtained through the use of original or
# modified versions of the software have to cite the authors by refering
# to the following publication:

# Maja Popović: "Hjerson: An Open Source Tool for Automatic Error
# Classification of Machine Translation Output". The Prague Bulletin of
# Mathematical Linguistics No. 96, pp. 59--68, October 2011
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


import sys
import math
import unicodedata
import argparse
import string

sent = False
backoff = False

class levNode:
    def __init__(self, rpos=0, hpos=0, error=0):
        self.rpos = rpos
        self.hpos = hpos
        self.error = error


def read_addfiles(addtext, addline, words):
    if addtext:
        addwords = addline.split()
    else:
        addwords = ["" for x in range(len(words))]
    return addwords

def adjust_indices(words, adjwords, addwords, adjaddwords):
    i = 1
    while i <= len(words):
        adjwords[i] = words[i-1]
        adjaddwords[i] = addwords[i-1]
        i += 1

def take_four_letters(line):
    bline=""
    words = line.strip().split()
    for w in words:
        bline+=w[:4]+" "
    
    return bline

def separate_punctuation(line):
    words = line.strip().split()
    tokenised = []
    for w in words:
        if len(w) == 1:
            tokenised.append(w)
        else:
            lastChar = w[-1]
            firstChar = w[0]
            if lastChar in string.punctuation:
                tokenised += [w[:-1], lastChar]
            elif firstChar in string.punctuation:
                tokenised += [firstChar, w[1:]]
            else:
                tokenised.append(w)

    return tokenised



def wer_errors(index, werwords, weradd, wererr, words, add, error):
    werwords.append(words[index])
    weradd.append(add[index])
    wererr.append(error)

def hyp_ref_errors(rline, rbaseline, hwords, hbases, error):
    rwords = rline.split()
    rbases = rbaseline.split()
    errors = []
    errorcount = 0.0
    inflerrorcount = 0.0

    for ihw, hw in enumerate(hwords):
        if hw in rwords:
            errors.append("x")
            n = rwords.index(hw)
            del rwords[n]
            del rbases[n]
        else:
            errors.append(error)
            errorcount += 1

    for ihb, hb in enumerate(hbases):
        if hb in rbases:
            if errors[ihb] == error:
                errors[ihb] = "i"+error
                n = rbases.index(hb)
                del rbases[n]
                inflerrorcount += 1
	 
    return errors, errorcount, inflerrorcount
   

def miss_ext_lex(wererrors, werwords, pererrors, errcats, misextcount, lexcount, misext):
    i = 0
    while i < len(wererrors):
        refWerWord = werwords[i]
        refWerError = wererrors[i]
        rperError  = pererrors[i]
        if rperError == "irerr" or rperError == "iherr":
            errcats.append("infl")
        elif rperError == "rerr" or rperError == "herr":
            if refWerError == "del" or refWerError == "ins":
                errcats.append(misext)
                misextcount += 1
            elif refWerError == "sub":
                errcats.append("lex")
                lexcount += 1
            else:
                errcats.append("x")
        else:
            errcats.append("x")
        i += 1

    return errcats, misextcount, lexcount

def reord(werreferrors, werrefwords, werhyperrors, werhypwords, hyperrcats, hypcount):
    referr = []
    i = 0
    while i < len(werreferrors):
        if werreferrors[i] != "x":
            referr.append(werrefwords[i])
        i += 1

    i = 0
    while i < len(werhyperrors):
        hypWerWord = werhypwords[i]
        hypWerError = werhyperrors[i]
        if hypWerError == "ins" or hypWerError == "del" or hypWerError == "sub":
            if hypWerWord in referr:
                hyperrcats[i] = "reord"
                hypcount += 1
                n = referr.index(hypWerWord)
                del referr[n]
        i += 1

    return hyperrcats, hypcount

def block_count(errcats, errcat, blockcount):
    i = 0
    newblock = True
    while i < len(errcats):
        cat = errcats[i]
        if cat == errcat:
            if newblock == True:
                blockcount += 1
                newblock = False
        else:
            newblock = True
            
        i += 1

    return blockcount


def write_error_rates(text, errorname, errorcount, errorrate):
    text.write(errorname+"\t"+str("%.0f" % errorcount)+"\t"+str("%.2f" % errorrate)+"\n")

def write_error_words(text, addtext, errors, words, add, title):
    text.write(title)
    for nr, r in enumerate(errors):
        if addtext:
            text.write(words[nr]+"#"+add[nr]+"~~"+r+" ")
        else:
            text.write(words[nr]+"~~"+r+" ")

    text.write("\n")

def write_error_cats(errcatfile, errcattext, addtext, words, add, cats, refhyp):
    if refhyp == "ref":
        errcattext.write(str(nSent)+"::ref-err-cats: ")
    elif refhyp == "hyp":
        errcattext.write(str(nSent)+"::hyp-err-cats: ")

    for nc, c in enumerate(cats):
        if addtext:
            addcat = "#"+add[nc]
        else:
            addcat = ""
        errcattext.write(words[nc]+addcat+"~~"+c+" ")

    errcattext.write("\n")
    if refhyp == "hyp":
        errcattext.write("\n")

def write_html(htmlfile, htmltext, addtext, words, add, cats, refhyp):
    if refhyp == "ref":
        htmltext.write("<u>REF:</u>  ")
    elif refhyp == "hyp":
        htmltext.write("<li>\n")
        htmltext.write("<u>HYP:</u> ")

    for nc, c in enumerate(cats):
        if addtext:
            addcat = "#"+add[nc]
        else:
            addcat = ""
        
        font = ""	
        closefont = "</font> "
        if c == "infl":
            font = "<font color=fuchsia>"
        elif c == "reord":
            font = "<font color=lime>"
        elif c == "lex":
            font = "<font color=red>"
        elif c == "miss" or c == "ext":
            font = "<font color=blue>"
        else:
            closefont = " "
        htmltxt.write(font+words[nc]+addcat+closefont)

    if refhyp == "ref":
        htmltxt.write("\n<br><br><br>\n")
    elif refhyp == "hyp":
        htmltxt.write("\n<br><br>\n")


def main():

    argParser = argparse.ArgumentParser()
    argParser.add_argument("-R", "--reference", help="reference translation", type=argparse.FileType('r'), required=True)
    argParser.add_argument("-H", "--hypothesis", help="hypothesis translation", type=argparse.FileType('r'), required=True)
    argParser.add_argument("-B", "--reference_base", help="reference base forms", type=argparse.FileType('r'))
    argParser.add_argument("-b", "--hypothesis_base", help="hypothesis base forms", type=argparse.FileType('r'))
    argParser.add_argument("-s", "--sent", help="show sentence level scores", action="store_true")
    argParser.add_argument("-A", "--reference_additional", help="reference: additional (POS, etc.)", type=argparse.FileType('r'))
    argParser.add_argument("-a", "--hypothesis_additional", help="hypothesis: additional (POS, etc.)", type=argparse.FileType('r'))
    argParser.add_argument("-c", "--err_cats", help="write error categories in a text file", type=argparse.FileType('w'))
    argParser.add_argument("-m", "--html", help="write error categories in a html file", type=argparse.FileType('w'))
    argParser.add_argument("-e", "--wer_errors", help="write WER error types in a text file", type=argparse.FileType('w'))
    args = argParser.parse_args()

    rline = args.reference.readline()
    hline = args.hypothesis.readline()

    if not(args.reference_base or args.hypothesis_base):
        baserline = take_four_letters(rline)
        basehline = take_four_letters(hline)
    else:
        baserline = args.reference_base.readline()
        basehline = args.hypothesis_base.readline()

    if args.reference_additional and args.hypothesis_additional:
        addrline = args.reference_additional.readline()
        addhline = args.hypothesis_additional.readline()
    else:
        addrline=""
        addhline=""

    if args.html:
        args.html.write("<html>\n")
        args.html.write("<head> <meta http-equiv=\"content-type\" content=\"text/html; charset=utf-8\"></meta> </head>\n\n")
        args.html.write("<body>\n\n")
        args.html.write("<font size=4>\n")
        args.html.write("<ol>\n")

    delim = "#+"

    totalHypLength = 0.0
    totalWerRefLength = 0.0

    totalWerCount = 0.0
    totalRperCount = 0.0
    totalHperCount = 0.0

    totalInflRperCount = 0.0
    totalInflHperCount = 0.0
    totalMissCount = 0.0
    totalExtCount = 0.0
    totalRefLexCount = 0.0
    totalHypLexCount = 0.0
    totalRefReordCount = 0.0
    totalHypReordCount = 0.0

    totalBlockInflRperCount = 0.0
    totalBlockInflHperCount = 0.0
    totalBlockMissCount = 0.0
    totalBlockExtCount = 0.0
    totalRefBlockLexCount = 0.0
    totalHypBlockLexCount = 0.0
    totalRefBlockReordCount = 0.0
    totalHypBlockReordCount = 0.0
    
    nSent = 0


    p = (0,0)

    Q = {}
    Q[p] = 0

    B = {}
    B[p] = levNode(0, 0, 0)
    

    while (hline and rline):

        # preparation

        nSent += 1

        minSentWer = 1000
        bestWerRefLength = 0.0
        bestWerRefIndex = -1
        bestWerRefErrors = []
        bestWerHypErrors = []
        bestWerRefWords = []
        bestWerHypWords = []
        bestWerRefAdd = []
        bestWerHypAdd = []

        bestSentWer = 0.0

        maxLength = []

        refs = rline.split("#+")
        if args.reference_additional:
            addrefs = addrline.split("#+")
        else:
            addrefs = ["" for x in range(len(refs))]
        baserefs = baserline.split("#+")


        # reading hypothesis
   
        hypWords = hline.split()
        addhypWords = read_addfiles(args.hypothesis_additional, addhline, hypWords)
        baseHypWords = basehline.split()

        totalHypLength += len(hypWords)


        # adjusting hypothesis indices to range from 1 to len(hypWords) (for WER calculation)

        hyp = {}
        addhyp = {}

        adjust_indices(hypWords, hyp, addhypWords, addhyp)

        # reading reference(s)

        nref = 0
    
        for reference in refs:
            ir = refs.index(reference)
            refWords = reference.split()
            addrefWords = read_addfiles(args.reference_additional, addrefs[ir], refWords)
            baseRefWords = baserefs[ir].split()


            # adjusting reference indices to range from 1 to len(refWords) (for WER calculation)

            ref = {}
            addref = {}

            adjust_indices(refWords, ref, addrefWords, addref)

           
            # maximal length (necessary for wer-alignment)

            if len(refWords) > len(hypWords):
                maxLength.append(len(refWords))
            else:
                maxLength.append(len(hypWords))



            # WER errors

            for nh in range(0, len(hyp)+1):
                p = (0, nh)
                Q[p] = nh
                B[p] = levNode(0, nh-1, 3)

            
            for nr in range(0, len(ref)+1):
                p = (nr, 0)
                Q[p] = nr
                B[p] = levNode(nr-1, 0, 2)
            

            p = (0, 0)
            B[p] = levNode(-1, -1, -1)
        
            p = (1, 0)
            B[p] = levNode(0, 0, 2)
        
            p = (0, 1)
            B[p] = levNode(0, 0, 3)


            # Qs and Bs

            for r in ref.keys():
                for h in hyp.keys():
                    minQ = 1000
                    p = (r, h)
                    dp = (r-1, h)
                    ip = (r, h-1)
                    sp = (r-1, h-1)


                    s = 0
                    if hyp[h] != ref[r]:
                        s = 1
                    else:
                        s = 0
                
                    if Q[sp]+s < minQ:
                        minQ = Q[sp]+s
                        B[p] = levNode(r-1, h-1, s)
        
                    if Q[dp]+1 < minQ:
                        minQ = Q[dp]+1
                        B[p] = levNode(r-1, h, 2)

                    if Q[ip]+1 < minQ:
                        minQ = Q[ip]+1
                        B[p] = levNode(r, h-1, 3)

                    Q[p] = minQ



            # backtracking
            
            sentWerCount = 0.0
            sentSubCount = 0.0
            sentDelCount = 0.0
            sentInsCount = 0.0

            l = maxLength[nref]
            werRefWords = []
            werHypWords = []
            werRefErrors = []
            werHypErrors = []
            werRefAdd = []
            werHypAdd = []

            # 1) starting backtracking
        
            p = (len(refWords), len(hypWords))

            err = B[p].error


            if err != 0:
                if err == 1:
                    wer_errors(len(refWords), werRefWords, werRefAdd, werRefErrors, ref, addref, "sub")
                    wer_errors(len(hypWords), werHypWords, werHypAdd, werHypErrors, hyp, addhyp, "sub")
                    sentSubCount += 1
                elif err == 2:
                    wer_errors(len(refWords), werRefWords, werRefAdd, werRefErrors, ref, addref, "del")
                    sentDelCount += 1
                elif err == 3:
                    wer_errors(len(hypWords), werHypWords, werHypAdd, werHypErrors, hyp, addhyp, "ins")
                    sentInsCount += 1
                
            else:
                wer_errors(len(refWords), werRefWords, werRefAdd, werRefErrors, ref, addref, "x")
                wer_errors(len(hypWords), werHypWords, werHypAdd, werHypErrors, hyp, addhyp, "x")


            # 2) going down


            rp = B[p].rpos
            hp = B[p].hpos


            while hp >= 0 and rp >= 0:
                p1 = (rp, hp)
                err = B[p1].error

            
                if err != 0:
                    if err == 1:
                        wer_errors(rp, werRefWords, werRefAdd, werRefErrors, ref, addref, "sub")
                        wer_errors(hp, werHypWords, werHypAdd, werHypErrors, hyp, addhyp, "sub")
                        sentSubCount += 1
                    elif err == 2:
                        wer_errors(rp, werRefWords, werRefAdd, werRefErrors, ref, addref, "del")
                        sentDelCount += 1
                    elif err == 3:
                        wer_errors(hp, werHypWords, werHypAdd, werHypErrors, hyp, addhyp, "ins")
                        sentInsCount += 1
                else:
                    wer_errors(rp, werRefWords, werRefAdd, werRefErrors, ref, addref, "x")
                    wer_errors(hp, werHypWords, werHypAdd, werHypErrors, hyp, addhyp, "x")
                
                l -= 1

                hp = B[p1].hpos
                rp = B[p1].rpos
            

        
            # best (minimum) sentence WER => best reference => best WER errors

            sentWerCount = sentSubCount + sentDelCount + sentInsCount
            sentWer = sentWerCount/len(refWords)
            if sentWer < minSentWer:
                minSentWer = sentWer
                bestWerRefIndex = ir
                bestWerRefLength = len(refWords)
                bestWerRefErrors = werRefErrors
                bestWerHypErrors = werHypErrors
                bestWerRefWords = werRefWords
                bestWerBaseRefWords = baseRefWords
                bestWerHypWords = werHypWords
                bestWerRefAdd = werRefAdd
                bestWerHypAdd = werHypAdd
                bestSentWer = sentWerCount
            
            nref += 1

            Q.clear()
            B.clear()


        totalWerRefLength += bestWerRefLength
        totalWerCount += bestSentWer

        bestWerRefErrors.reverse()
        bestWerHypErrors.reverse()
        bestWerRefWords.reverse()
        bestWerHypWords.reverse()
        bestWerRefAdd.reverse()
        bestWerHypAdd.reverse()


        # preparations for HPER and RPER

        refWords = refs[bestWerRefIndex].split()
        read_addfiles(args.reference_additional, addrefs[bestWerRefIndex], refWords)
        baseRefWords = baserefs[bestWerRefIndex].split()

        if len(hypWords) == 0:
            hLen = 0.00000001
        else:
            hLen = len(hypWords)


        # HPER (hypothesis/precision) errors
    
        hperErrors = []
        sentHperCount = 0.0
        sentInflHperCount = 0.0

        hperErrors, sentHperCount, sentInflHperCount = hyp_ref_errors(refs[bestWerRefIndex], baserefs[bestWerRefIndex], hypWords, baseHypWords, "herr")


        sentHper = sentHperCount/hLen
        sentInflHper = sentInflHperCount/hLen
    
    

        # RPER (reference/recall) errors
        
        rperErrors = []
        sentRperCount = 0.0
        sentInflRperCount = 0.0
            
        rperErrors, sentRperCount, sentInflRperCount = hyp_ref_errors(hline, basehline, refWords, baseRefWords, "rerr")

        sentRper = sentRperCount/len(refWords)
        sentInflRper = sentInflRperCount/len(refWords)
    


        totalHperCount += sentHperCount
        totalRperCount += sentRperCount
        totalInflRperCount += sentInflRperCount
        totalInflHperCount += sentInflHperCount
  

 
        # preparations for error categorisation
          

        refErrorCats = []
        hypErrorCats = []
    
        sentMissCount = 0.0
        sentExtCount = 0.0
        sentRefLexCount = 0.0
        sentHypLexCount = 0.0
        sentRefReordCount = 0.0
        sentHypReordCount = 0.0

        sentBlockInflRperCount = 0.0
        sentBlockInflHperCount = 0.0
        sentBlockMissCount = 0.0
        sentBlockExtCount = 0.0
        sentRefBlockLexCount = 0.0
        sentHypBlockLexCount = 0.0
        sentRefBlockReordCount = 0.0
        sentHypBlockReordCount = 0.0

    
        # missing words, reference lexical errors, reference inflectional errors
    

        refErrorCats, sentMissCount, sentRefLexCount = miss_ext_lex(bestWerRefErrors, bestWerRefWords, rperErrors, refErrorCats, sentMissCount, sentRefLexCount, "miss")


        # extra words, hypothesis lexical errors, hypothesis inflectional errors
  
        hypErrorCats, sentExtCount, sentHypLexCount = miss_ext_lex(bestWerHypErrors, bestWerHypWords, hperErrors, hypErrorCats, sentExtCount, sentHypLexCount, "ext")


        # reordering errors

        hypErrorCats, sentHypReordCount = reord(bestWerRefErrors, bestWerRefWords, bestWerHypErrors, bestWerHypWords, hypErrorCats, sentHypReordCount)

        refErrorCats, sentRefReordCount = reord(bestWerHypErrors, bestWerHypWords, bestWerRefErrors, bestWerRefWords, refErrorCats, sentRefReordCount)


        # block error counts and error rates

        sentBlockInflRperCount = block_count(refErrorCats, "infl", sentBlockInflRperCount)
        sentBlockInflHperCount = block_count(hypErrorCats, "infl", sentBlockInflHperCount)
        sentBlockMissCount = block_count(refErrorCats, "miss", sentBlockMissCount)
        sentBlockExtCount = block_count(hypErrorCats, "ext", sentBlockExtCount)
        sentRefBlockReordCount = block_count(refErrorCats, "reord", sentRefBlockReordCount)
        sentHypBlockReordCount = block_count(hypErrorCats, "reord", sentHypBlockReordCount)
        sentRefBlockLexCount = block_count(refErrorCats, "lex", sentRefBlockLexCount)
        sentHypBlockLexCount = block_count(hypErrorCats, "lex", sentHypBlockLexCount)

        totalMissCount += sentMissCount
        totalExtCount += sentExtCount
        totalRefLexCount += sentRefLexCount
        totalHypLexCount += sentHypLexCount
        totalRefReordCount += sentRefReordCount
        totalHypReordCount += sentHypReordCount

        totalBlockInflRperCount += sentBlockInflRperCount
        totalBlockInflHperCount += sentBlockInflHperCount
        totalBlockMissCount += sentBlockMissCount
        totalBlockExtCount += sentBlockExtCount
        totalRefBlockReordCount += sentRefBlockReordCount
        totalHypBlockReordCount += sentHypBlockReordCount
        totalRefBlockLexCount += sentRefBlockLexCount
        totalHypBlockLexCount += sentHypBlockLexCount


        # write sentence error rates
    
        if sent:
            wer = 100*minSentWer
            hper = 100*sentHper
            rper = 100*sentRper
 
            iHper = 100*sentInflHper
            iRper = 100*sentInflRper
            missErr = 100*sentMissCount/bestWerRefLength
            extErr = 100*sentExtCount/hLen
            rLexErr = 100*sentRefLexCount/bestWerRefLength
            hLexErr = 100*sentHypLexCount/hLen
            rRer = 100*sentRefReordCount/bestWerRefLength
            hRer = 100*sentHypReordCount/hLen

            biHper = 100*sentBlockInflHperCount/hLen
            biRper = 100*sentBlockInflRperCount/bestWerRefLength
            rbRer =  100*sentRefBlockReordCount/bestWerRefLength
            hbRer = 100*sentHypBlockReordCount/hLen
            bmissErr = 100*sentBlockMissCount/bestWerRefLength
            bextErr = 100*sentBlockExtCount/hLen
            rbLexErr = 100*sentRefBlockLexCount/bestWerRefLength
            hbLexErr = 100*sentHypBlockLexCount/hLen
    
            sumCount = sentInflHperCount + sentMissCount + sentHypLexCount + sentExtCount + sentHypReordCount
            bsumCount =  sentBlockInflHperCount + sentBlockMissCount + sentHypBlockLexCount + sentBlockExtCount + sentHypBlockReordCount
            sumErr = iHper + hRer + missErr + extErr + hLexErr
            bsumErr = biHper + hbRer + bmissErr + bextErr + hbLexErr
            rbsumCount = sentInflHperCount + sentMissCount + sentHypLexCount + sentExtCount + sentHypBlockReordCount
            rbsumErr =  iHper + hbRer + missErr + extErr + hLexErr
        
            write_error_rates(errtxt, str(nSent)+"::Wer: ", bestSentWer, wer)
            write_error_rates(errtxt, str(nSent)+"::Rper: ", sentRperCount, rper)
            write_error_rates(errtxt, str(nSent)+"::Hper: ", sentHperCount, hper)

            errtxt.write("\n")

            write_error_rates(errtxt, str(nSent)+"::SUMerr: ", sumCount, sumErr)
            write_error_rates(errtxt, str(nSent)+"::bSUMerr: ", bsumCount, bsumErr)
            write_error_rates(errtxt, str(nSent)+"::rbSUMerr: ", rbsumCount, rbsumErr)
        
            errtxt.write("\n")


            write_error_rates(errtxt, str(nSent)+"::refINFer: ", sentInflRperCount, iRper)
            write_error_rates(errtxt, str(nSent)+"::hypINFer: ", sentInflHperCount, iHper)
            write_error_rates(errtxt, str(nSent)+"::refRer:   ", sentRefReordCount, rRer)
            write_error_rates(errtxt, str(nSent)+"::hypRer:   ", sentHypReordCount, hRer)
            write_error_rates(errtxt, str(nSent)+"::MISer:  ", sentMissCount, missErr)
            write_error_rates(errtxt, str(nSent)+"::EXTer:  ", sentExtCount, extErr)
            write_error_rates(errtxt, str(nSent)+"::refLEXer: ", sentRefLexCount, rLexErr)
            write_error_rates(errtxt, str(nSent)+"::hypLEXer: ", sentHypLexCount, hLexErr)

            errtxt.write("\n")

            write_error_rates(errtxt, str(nSent)+"::brefINFer: ", sentBlockInflRperCount, biRper)
            write_error_rates(errtxt, str(nSent)+"::bhypINFer: ", sentBlockInflHperCount, biHper)
            write_error_rates(errtxt, str(nSent)+"::brefRer:   ", sentRefBlockReordCount, rbRer)
            write_error_rates(errtxt, str(nSent)+"::bhypRer:   ", sentHypBlockReordCount, hbRer)
            write_error_rates(errtxt, str(nSent)+"::bMISer:  ", sentBlockMissCount, bmissErr)
            write_error_rates(errtxt, str(nSent)+"::bEXTer:  ", sentBlockExtCount, bextErr)
            write_error_rates(errtxt, str(nSent)+"::brefLEXer: ", sentRefBlockLexCount, rbLexErr)
            write_error_rates(errtxt, str(nSent)+"::bhypLEXer: ", sentHypBlockLexCount, hbLexErr)

            errtxt.write("\n")


        # write wer, rper and hper words (and additional information, such as POS, etc.)

        if args.wer_errors:
            write_error_words(args.wer_errors, args.reference_additional, bestWerRefErrors, bestWerRefWords, bestWerRefAdd, str(nSent)+"::wer-ref-errors: ")
            write_error_words(args.wer_errors, args.hypothesis_additional, bestWerHypErrors, bestWerHypWords, bestWerHypAdd, str(nSent)+"::wer-hyp-errors: ")

            args.wer_errors.write("\n")

            write_error_words(args.wer_errors, args.reference_additional, rperErrors, refWords, addrefWords, str(nSent)+"::ref-errors: ")
            write_error_words(args.wer_errors, args.hypothesis_additional, hperErrors, hypWords, addhypWords, str(nSent)+"::hyp-errors: ")

            args.wer_errors.write("\n\n")


        # write error categories (and additional information, such as POS, etc.)

        if args.err_cats: ## REDUNDANCY WITH FILES!!! CHANGE ALL READ/WRITE FUNCTIONS
            write_error_cats(args.err_cats, args.err_cats, args.reference_additional, refWords, bestWerRefAdd, refErrorCats, "ref")
            write_error_cats(args.err_cats, args.err_cats, args.hypothesis_additional, hypWords, bestWerHypAdd, hypErrorCats, "hyp")

        if args.html: ## REDUNDANCY WITH FILES!!! CHANGE ALL READ/WRITE FUNCTIONS
            write_html(args.html, args.html, args.hypothesis_additional, hypWords, bestWerHypAdd, hypErrorCats, "hyp")
            write_html(args.html, args.html, args.reference_additional, refWords, bestWerRefAdd, refErrorCats, "ref")



        hline = args.hypothesis.readline()
        rline = args.reference.readline()

        if not (args.reference_base or args.hypothesis_base):
            baserline = take_four_letters(rline)
            basehline = take_four_letters(hline)
        else:
            baserline = args.reference_base.readline()
            basehline = args.hypothesis_base.readline()

        if args.reference_additional and args.hypothesis_additional:
            addrline = args.reference_additional.readline()
            addhline = args.hypothesis_additional.readline()
        else:
            addrline = ""
            addhline = ""

    if args.html:
        args.html.write("</ol>\n\n")
        args.html.write("</font>\n\n")
        args.html.write("</body>\n\n")
        args.html.write("</html>")


    # calculate and write total error rates


    sys.stdout.write("\n")

    totalWer = 100*totalWerCount/totalWerRefLength
    totalHper = 100*totalHperCount/totalHypLength
    totalRper = 100*totalRperCount/totalWerRefLength

    totalInflHper = 100*totalInflHperCount/totalHypLength
    totalInflRper = 100*totalInflRperCount/totalWerRefLength
    totalMissErr = 100*totalMissCount/totalWerRefLength
    totalExtErr = 100*totalExtCount/totalHypLength
    totalrLexErr = 100*totalRefLexCount/totalWerRefLength
    totalhLexErr = 100*totalHypLexCount/totalHypLength
    totalrRer = 100*totalRefReordCount/totalWerRefLength
    totalhRer = 100*totalHypReordCount/totalHypLength

    totalbiHper = 100*totalBlockInflHperCount/totalHypLength
    totalbiRper = 100*totalBlockInflRperCount/totalWerRefLength
    totalrbRer = 100*totalRefBlockReordCount/totalWerRefLength
    totalhbRer = 100*totalHypBlockReordCount/totalHypLength
    totalbmissErr = 100*totalBlockMissCount/totalWerRefLength
    totalbextErr = 100*totalBlockExtCount/totalHypLength
    totalrbLexErr = 100*totalRefBlockLexCount/totalWerRefLength
    totalhbLexErr = 100*totalHypBlockLexCount/totalHypLength

    totalSumCount = totalInflHperCount + totalMissCount + totalHypLexCount + totalExtCount + totalHypReordCount
    totalSumErr = totalInflHper + totalhRer + totalMissErr + totalExtErr + totalhLexErr
    totalBlockSumCount = totalBlockInflHperCount + totalBlockMissCount + totalHypBlockLexCount + totalBlockExtCount + totalHypBlockReordCount
    totalBlockSumErr = totalbiHper + totalhbRer + totalbmissErr + totalbextErr + totalhbLexErr
    totalRBSumCount = totalInflHperCount + totalMissCount + totalHypLexCount + totalExtCount + totalHypBlockReordCount
    totalRBSumErr = totalInflHper + totalhbRer + totalMissErr + totalExtErr + totalhLexErr

    write_error_rates(sys.stdout, "Wer:  ", totalWerCount, totalWer)
    write_error_rates(sys.stdout, "Rper: ", totalRperCount, totalRper)
    write_error_rates(sys.stdout, "Hper: ", totalHperCount, totalHper)

    sys.stdout.write("\n")

    write_error_rates(sys.stdout, "SUMerr: ", totalSumCount, totalSumErr)
    write_error_rates(sys.stdout, "bSUMerr: ", totalBlockSumCount, totalBlockSumErr)
    write_error_rates(sys.stdout, "rbSUMerr: ", totalRBSumCount, totalRBSumErr)

    sys.stdout.write("\n")

    write_error_rates(sys.stdout, "refINFer: ", totalInflRperCount, totalInflRper)
    write_error_rates(sys.stdout, "hypINFer: ", totalInflHperCount, totalInflHper)
    write_error_rates(sys.stdout, "refRer:   ", totalRefReordCount, totalrRer)
    write_error_rates(sys.stdout, "hypRer:   ", totalHypReordCount, totalhRer)
    write_error_rates(sys.stdout, "MISer:  ", totalMissCount, totalMissErr)
    write_error_rates(sys.stdout, "EXTer:  ", totalExtCount, totalExtErr)
    write_error_rates(sys.stdout, "refLEXer: ", totalRefLexCount, totalrLexErr)
    write_error_rates(sys.stdout, "hypLEXer: ", totalHypLexCount, totalhLexErr)

    sys.stdout.write("\n")

    write_error_rates(sys.stdout, "brefINFer: ", totalBlockInflRperCount, totalbiRper)
    write_error_rates(sys.stdout, "bhypINFer: ", totalBlockInflHperCount, totalbiHper)
    write_error_rates(sys.stdout, "brefRer:   ", totalRefBlockReordCount, totalrbRer)
    write_error_rates(sys.stdout, "bhypRer:   ", totalHypBlockReordCount, totalhbRer)
    write_error_rates(sys.stdout, "bMISer:  ", totalBlockMissCount, totalbmissErr)
    write_error_rates(sys.stdout, "bEXTer:  ", totalBlockExtCount, totalbextErr)
    write_error_rates(sys.stdout, "brefLEXer: ", totalRefBlockLexCount, totalrbLexErr)
    write_error_rates(sys.stdout, "bhypLEXer: ", totalHypBlockLexCount, totalhbLexErr)

    sys.stdout.write("\n")

if __name__ == "__main__":
    main()






