
from __future__ import print_function
import sys, re
from sys import argv, stdin
from subprocess import Popen, PIPE
from time import sleep 
import select


class SyntaxError( Exception ):
    """When we run into an unexpected token, this is the exception to use"""
    def __init__(self, pos = None, msg = "Bad Token" ):
        Exception.__init__( self )
        self.pos = pos
        self.msg = msg

    def __str__(self):
        if not self.pos:
            return 'SyntaxError'
        else:
            return 'SyntaxError@%s (%s)' % (repr(self.pos), self.msg)

class BoardException( Exception ) :
    def __init__(self, msg = "Bad move" ):
        Exception.__init__( self )
        self.msg = msg

    def __str__(self):
        return self.msg

##############################################################################################################    

class ChessMovePair( object ) :
    def __init__( self, moveNumber, whiteMove, blackMove ):
        self.moveNumber = moveNumber
        self.whiteMove = whiteMove
        self.blackMove = blackMove
        self.whiteMoveCP = None
        self.blackMoveCP = None
        self.comments = dict()

    def setComment( self, place, comment ) :
        self.comments[ place ] = comment

        
class ChessGame( object ) :
    def __init__( self ) :
        self.tags = list()
        self.moves = list()
        self.lastMove = None

    def addTag( self, tag ) :
        self.tags.append( tag )

    # TODO: ignore comments in first step and add them later
    def addMove( self, moveNumber, whiteMove, blackMove ) :
        if self.lastMove == None or self.lastMove.moveNumber != moveNumber :
            self.lastMove = ChessMovePair( moveNumber, whiteMove, blackMove )
            self.moves.append( self.lastMove )
        else :
            if whiteMove :
                self.lastMove.whiteMove = whiteMove
            if blackMove :
                self.lastMove.blackMove = blackMove


    def print( self ) :
        for move in self.moves :
            print( "%s" % ( move.moveNumber ), end = "" )
            print( "%s" % ( move.whiteMove if move.whiteMove else ".." ), end = "" )
            if move.whiteMoveCP :
                print( "{%s}" % ( move.whiteMoveCP ), end = "" )
            print( "%s" % ( move.blackMove if move.blackMove else "" ), end = "" )
            if move.blackMoveCP :
                print( "{%s}" % ( move.blackMoveCP ), end = "" )
            print()
       
##############################################################################################################    

class Scanner( object ) :
    READ_BLOCK_SIZE = 4096
    def __init__( self, filename ) :
        self.grabInput( filename )
        self.scanPosition = 0
        self.ignored = re.compile( r'\s+' )
        pass

    def grabInput( self, filename ) :
        self.input = ""
        f = open( filename, "r" )
        data = f.read( self.READ_BLOCK_SIZE )
        while data :
            self.input = self.input + data
            data = f.read( self.READ_BLOCK_SIZE )
    
    def peek( self, regularExpression ) :
        self.ignore()
        m = regularExpression.match( self.input, self.scanPosition )
        if m :
            return m.group( 0 )
        return m

    def scan( self, regularExpression ) :
        self.ignore()
        m = regularExpression.match( self.input, self.scanPosition )
        if m :
            self.scanPosition = m.end()
            return m.group( 0 )
        else :
            raise SyntaxError( self.scanPosition, regularExpression )

    def ignore( self ) :
        m = self.ignored.match( self.input, self.scanPosition )
        if m :
            self.scanPosition = m.end()

            
##############################################################################################################    

class PgnParser( object ) :
    TAGTEXT = re.compile( r"\[[^\]]*\]" )
    COMMENT1START = re.compile( r'\(' )
    COMMENT1END = re.compile( r'\)' )
    COMMENT2START = re.compile( r'{' )
    COMMENT2END = re.compile( r'}' )
    COMMENTTEXT = re.compile( r'[^{}()]+' )
    MOVENUMBER = re.compile( r"[0-9]+\." )
    PIECEMOVE = re.compile( r"[KQBNR]?[a-h]?[1-8]?x?[a-h][1-8][+#]?[!?]?[!?]?|O-O|O-O-O" )
    PIECEPLACEHOLDER = re.compile( r'\.\.' )
    GAMERESULT = re.compile( r'1-0|0-1|\*|1/2-1/2' )
    
    def __init__( self, scanner ) :
        self.scanner = scanner
        self.chessGame = ChessGame()

    def game( self ) :
        self.tags()
        self.comments()
        self.moves()
        return self.chessGame

    def tags( self ) :
        while self.scanner.peek( self.TAGTEXT ) :
            self.tag()


    def tag( self ) :
        tagtext = self.scanner.scan( self.TAGTEXT )
        print( "Tag: %s" % tagtext )
        return tagtext

    def moves( self ) :
        m = self.move()
        while m :
            print( "Move: %s %s %s" % m )
            m = self.move()

    def move( self ) :
        # print( "Scan moves" )
        if not self.scanner.peek( self.MOVENUMBER ) :
            return None
        moveNumber = self.scanner.scan( self.MOVENUMBER )
        comment = self.comments()
        if comment :
            # print( "Comment: %s" % comment )
            pass
        if self.scanner.peek( self.PIECEPLACEHOLDER ) :
           self.scanner.scan( self.PIECEPLACEHOLDER )
           comment = self.comments()
           if comment :
               # print( "Comment: %s" % comment )
               pass
           pieceMoveBlack = self.scanner.scan( self.PIECEMOVE )
           comment = self.comments()
           if comment :
               # print( "Comment: %s" % comment )
               pass
           self.chessGame.addMove( moveNumber, None, pieceMoveBlack )
           return ( moveNumber, None, pieceMoveBlack )
        else :
           pieceMoveWhite = self.scanner.scan( self.PIECEMOVE )
           comment = self.comments()
           if comment :
               # print( "Comment: %s" % comment )
               pass
           if self.scanner.peek( self.PIECEMOVE ) :
               pieceMoveBlack = self.scanner.scan( self.PIECEMOVE )
               comment = self.comments()
               if comment :
                   # print( "Comment: %s" % comment )
                   pass
               self.chessGame.addMove( moveNumber, pieceMoveWhite, pieceMoveBlack )
               return ( moveNumber, pieceMoveWhite, pieceMoveBlack )
           else :
               self.chessGame.addMove( moveNumber, pieceMoveWhite, None )
               return ( moveNumber, pieceMoveWhite, None )

    def comments( self ) :
        # print( "Scan comments" )
        c = None
        c1 = self.comment()
        while c1 :
            if c == None :
                c = c1
            else :
                c = c + c1
            c1 = self.comment()
        return c

    def comment( self ) :
        # print( "Scan comment" )
        c1 = self.comment1()
        if c1:
            return c1
        return self.comment2()
    
    def comment1( self ) :
        if not self.scanner.peek( self.COMMENT1START ) :
            # print( "Scan comment1: no start found" )
            return None
        # print( "Scan comment1" )
        c = self.scanner.scan( self.COMMENT1START )
        matchFound = True
        while matchFound : 
            matchFound = False
            if self.scanner.peek( self.COMMENTTEXT ) :
                c = c + self.scanner.scan( self.COMMENTTEXT )
                matchFound = True
            c1 = self.comments()
            if c1 :
                c = c + c1
                matchFound = True
        c = c + self.scanner.scan( self.COMMENT1END )
        # print( "Comment1: %s" % c )
        return c

    def comment2( self ) :
        if not self.scanner.peek( self.COMMENT2START ) :
            # print( "Scan comment2: no start found" )
            return None
        # print( "Scan comment2" )
        c = self.scanner.scan( self.COMMENT2START )
        matchFound = True
        while matchFound : 
            matchFound = False
            if self.scanner.peek( self.COMMENTTEXT ) :
                c = c + self.scanner.scan( self.COMMENTTEXT )
                matchFound = True
            c1 = self.comments()
            if c1 :
                c = c + c1
                matchFound = True
        c = c + self.scanner.scan( self.COMMENT2END )
        # print( "Comment2: %s" % c )
        return c


##############################################################################################################    

class Square( object ) :
    def __init__( self, color, figure ) :
        self.color = color
        self.figure = figure
        pass

class Board( object ) :
   STARTPOS_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
   PGN_MOVE_ENCODING = re.compile( r'([KQBNR]?)([a-h]?[1-8]?)(x?)([a-h][1-8])[+#]?[!?]?[!?]?' )

   def __init__( self, cloneBoard = None ) :
       if cloneBoard :
           self.clone( cloneBoard )
       else:
           self.initializeEmptyBoard()

   def initializeEmptyBoard( self ) : 
       color = "w"
       figure = " "
       self.squares = list()
       for r in xrange( 1, 9 ):
           color = "w" if color == "b" else "b" 
           for f in xrange( 1, 9 ) : 
               self.squares.append( Square( color, figure ) ) 
               color = "w" if color == "b" else "b" 
       # print( "we have %s squares" % len( self.squares ) ) 
       
   def move( self, m ) :
       pass 

   def clone( self, cloneBoard ) :
       self.squares = list()
       for sq in cloneBoard.squares :
           self.squares.append( Square( sq.color, sq.figure ) )
           
       
   def getSquare( self, p ) :
       # p[ 0 ] -> file ( 1 - 8 aka a - h )
       # p[ 1 ] -> rank ( 1 - 8 )
       return self.squares[ ( p[ 1 ] - 1 ) * 8 + ( p[ 0 ]  - 1 )]

   def setSquare( self, p, figure ) :
       # print( "setSquare %s %s %s" % ( r,f, figure ) )
       self.squares[( p[ 1 ] - 1 ) * 8 + ( p[ 0 ]  -1 )].figure = figure

   def readFen( self, fen ) :
       figuresString = fen.split()[ 0 ]
       r = 8
       f = 1 
       for c in figuresString :
           if c == "/" :
               r -= 1
               f = 1
           elif ord( c ) <= ord( "8" ) and ord( c ) >= ord( "1" ) :
               f+= ord( c ) - ord( "0" )
           else :
               self.setSquare( ( f, r ), c )
               f += 1

   def startPosition( self ) :
        self.readFen( self.STARTPOS_FEN )
        
   def print( self ) :
       print()
       print()
       r = 8
       print( "  ---------------------------------" )
       while r > 0 :
            print( "  |   |   |   |   |   |   |   |   |" )
            print( "%s " % r, end = "" )
            for f in xrange( 1, 9 ) :
                sq = self.getSquare( ( f, r ) )
                print( "| %s " % ( sq.figure ), end = "" )
            r-= 1
            print("|" )
            print( "  |   |   |   |   |   |   |   |   |" )
            print( "  ---------------------------------" )
            print()
       print( "    a   b   c   d   e   f   g   h" )
       print()
   
   def checkMove( self, figure, dst, stepList, iterative ) :
       figureSquares = []
       for step in stepList : 
           p2 = ( dst[ 0 ] + step[ 0 ], dst[ 1 ] + step[ 1 ] )
           while p2[ 0 ] > 0 and p2[ 0 ] < 9 and p2[ 1 ] > 0 and p2[ 1 ] < 9 :
               square = self.getSquare( p2 )
               if square.figure != " " :
                   if square.figure == figure :
                       figureSquares.append( p2 )
                   break
               if not iterative :
                    break
               p2 = ( p2[ 0 ] + step[ 0 ], p2[ 1 ] + step[ 1 ] )
       print( "Check square %s for figure %s found %s" % ( p2, figure, figureSquares ) )
       return figureSquares

       
   def checkKingMove( self, figure, dst ) :
       stepList = ( ( 1, 0 ), ( -1, 0 ), ( 0, 1 ), ( 0, -1 ), ( 1, 1 ), ( -1, 1 ), ( 1, -1 ), ( -1, -1 ) )
       return self.checkMove( figure, dst, stepList, False )

       
   def checkQueenMove( self, figure, dst ) :
       stepList = ( ( 1, 0 ), ( -1, 0 ), ( 0, 1 ), ( 0, -1 ), ( 1, 1 ), ( -1, 1 ), ( 1, -1 ), ( -1, -1 ) )
       return self.checkMove( figure, dst, stepList, True )

   
   def checkRookMove( self, figure, dst ) :
       stepList = ( ( 1, 0 ), ( -1, 0 ), ( 0, 1 ), ( 0, -1 ) )
       return self.checkMove( figure, dst, stepList, True )

   
   def checkBishopMove( self, figure, dst ) :
       stepList = ( ( 1, 1 ), ( -1, 1 ), ( 1, -1 ), ( -1, -1 ) )
       return self.checkMove( figure, dst, stepList, True )

   
   def checkKnightMove( self, figure, dst ) :
       stepList = ( ( 2, 1 ), ( 2, -1 ), ( -2, 1 ), ( -2, -1 ), ( 1, 2 ), ( -1, 2 ), ( 1, -2 ), ( -1, -2 )  )
       return self.checkMove( figure, dst, stepList, False )

   
   def checkPawnMove( self, figure, dst, color, captures ) :
       if color == "w" :
           if captures :
               # TODO handle en passant capture
               stepList = ( ( 1, -1 ), ( -1, -1 ) )
           else:
               stepList = [ ( 0, -1 ) ]
               if dst[ 1 ] == 4 :
                   stepList.append( ( 0, -2 ) )
       else :
           if captures :
               # TODO handle en passant capture
               stepList = ( ( 1, 1 ), ( -1, 1 ) )
           else:
               stepList = [ ( 0, 1 ) ]
               if dst[ 1 ] == 5 :
                   stepList.append( ( 0, 2 ) )
       return self.checkMove( figure, dst, stepList, False )

   
   def positionStringToTupple( self, position ) :
       # position can be 'a1', 'a', '1', ''
       l = len( position )
       if l == 0 :
           return ( 0, 0 )
       elif l == 1 : 
           r = ord( position ) - ord( '1' ) + 1
           if r > 0 and r < 9:
               return ( 0, r )
           else :
               f = ord( position ) - ord( 'a' ) + 1
               return ( f, 0 ) 
       else:
           f = ord( position[ 0 ] ) - ord( 'a' ) + 1
           r = ord( position[ 1 ] ) - ord( '1' ) + 1
           return ( f, r )
           
           
   def positionTuppleToString( self, position ) :
       return "%s%s" % ( str( unichr( ord( 'a' ) + position[ 0 ] - 1) ),
                         str( unichr( ord( '1' ) + position[ 1 ] - 1 ) ) )

   
   def moveFigureOnBoard( self, color, figure, dst, captures ) :
       coloredFigure = self.coloredFigure( figure, color )
       figure = coloredFigure.upper()
       if figure == "K" :
           squares = self.checkKingMove( coloredFigure, dst )
       elif figure == "Q" :
           squares = self.checkQueenMove( coloredFigure, dst )
       elif figure == "R" :
           squares = self.checkRookMove( coloredFigure, dst )
       elif figure == "B" :
           squares = self.checkBishopMove( coloredFigure, dst )
       elif figure == "N" :
           squares = self.checkKnightMove( coloredFigure, dst )
       elif figure == "P" :
           squares = self.checkPawnMove( coloredFigure, dst, color, captures )
       else:
           raise BoardException( "Unknown figure %s" % figure )
       return squares 


   def coloredFigure( self, figure, color ) :
       cf = figure if figure != "" else "p"
       cf = cf.upper() if color == "w" else cf.lower()
       return cf

   def movePgn( self, move, color ) :
       # white uppercase, black lowercase
       algebraicMove = self.testCastlingPgn( move, color )
       if algebraicMove :
           return algebraicMove

       moveMatch = self.PGN_MOVE_ENCODING.match( move )
       if moveMatch :
           print( "Found match: %s" % moveMatch.group( 0 ) )
           figure = moveMatch.group( 1 )
           coloredFigure = self.coloredFigure( figure, color )
           fromFileAndRank = moveMatch.group( 2 )
           captures =  True if moveMatch.group( 3 ) == "x" else False
           toFileAndRank  = moveMatch.group( 4 )
           print( "Move %s from %s to %s color %s" % ( coloredFigure, fromFileAndRank, toFileAndRank, color ) )
           dst = self.positionStringToTupple( toFileAndRank )
           srcHint = self.positionStringToTupple( fromFileAndRank )
           squares = self.moveFigureOnBoard( color, figure, dst, captures )
           print( "Found possible source squares: %s" % ( squares ) )
           if len( squares ) == 0 :
               raise BoardException( "No figure found" )
           elif len( squares ) == 1 :
               src = squares[ 0 ]
               fromFileAndRank = self.positionTuppleToString( src )
               self.setSquare( src, " " )
               self.setSquare( dst, coloredFigure )
           else :
               for src in squares :
                   if srcHint[ 0 ] == src[ 0 ] and srcHint[ 1 ] == src[ 1 ] :
                       fromFileAndRank = self.positionTuppleToString( src )
                       self.setSquare( src, " " )
                       self.setSquare( dst, coloredFigure )
                       break
                   elif srcHint[ 0 ] == src[ 0 ]  :
                       fromFileAndRank = self.positionTuppleToString( src )
                       self.setSquare( src, " " )
                       self.setSquare( dst, coloredFigure )
                       break
                   elif srcHint[ 1 ] == src[ 1 ]  :
                       fromFileAndRank = self.positionTuppleToString( src )
                       self.setSquare( src, " " )
                       self.setSquare( dst, coloredFigure )
                       break
           algebraicMove = "%s%s" % ( fromFileAndRank, toFileAndRank )
           print( "algebraicMove: %s" % algebraicMove )
           return algebraicMove
       raise BoardException( "Unknown move %s for %s" % ( move, color ) )
       return None

   
   def testCastlingPgn( self, m, color ) :
       if color == "w" and m == "O-O" :
           self.setSquare( ( 5, 1 ), " " )
           self.setSquare( ( 8, 1 ), " " )
           self.setSquare( ( 7, 1 ), "K" )
           self.setSquare( ( 6, 1 ), "R" )
           return "e1g1"
       elif color == "w" and m == "O-O-O" :
           self.setSquare( ( 5, 1 ), " " )
           self.setSquare( ( 1, 1 ), " " )
           self.setSquare( ( 3, 1 ), "K" )
           self.setSquare( ( 4, 1 ), "R" )
           return "e1c1"
       elif color == "b" and m == "O-O" :
           self.setSquare( ( 5, 8 ), " " )
           self.setSquare( ( 8, 8 ), " " )
           self.setSquare( ( 7, 8 ), "k" )
           self.setSquare( ( 6, 8 ), "r" )
           return "e8g8" 
       elif color == "b" and m == "O-O-O" :
           self.setSquare( ( 5, 8 ), " " )
           self.setSquare( ( 8, 8 ), " " )
           self.setSquare( ( 3, 8 ), "k" )
           self.setSquare( ( 4, 8 ), "r" )
           return "e8c8" 
       return None 

   
   def testCastlingAgebraic( self, m ) :
       if m == "e1g1" :
           self.setSquare( ( 5, 1 ), " " )
           self.setSquare( ( 8, 1 ), " " )
           self.setSquare( ( 7, 1 ), "K" )
           self.setSquare( ( 6, 1 ), "R" )
           return "O-O"
       elif m == "e1c1" :
           self.setSquare( ( 5, 1 ), " " )
           self.setSquare( ( 1, 1 ), " " )
           self.setSquare( ( 3, 1 ), "K" )
           self.setSquare( ( 4, 1 ), "R" )
           return "O-O-O"
       elif m == "e8g8" :
           self.setSquare( ( 5, 8 ), " " )
           self.setSquare( ( 8, 8 ), " " )
           self.setSquare( ( 7, 8 ), "k" )
           self.setSquare( ( 6, 8 ), "r" )
           return "O-O"
       elif m == "e8c8" :
           self.setSquare( ( 5, 8 ), " " )
           self.setSquare( ( 8, 8 ), " " )
           self.setSquare( ( 3, 8 ), "k" )
           self.setSquare( ( 4, 8 ), "r" )
           return "O-O-O"
       return None

   
   def moveAlgebraic( self, m, color ) :
       pgnString =  self.testCastlingAgebraic( m )
       if pgnString :
           return pgnString

       srcString = m[0:2]
       dstString = m[2:]
       src = self.positionStringToTupple( m[0:2] )
       dst = self.positionStringToTupple( m[2:] )
       coloredFigure = self.getSquare( src ).figure
       figure = coloredFigure.upper()
       figureDst = self.getSquare( dst ).figure.upper()
       # TODO handle 'en passant'
       captures = figureDst != " "
       captureString = "x" if captures else ""
       
       print( "Search for %s on square %s %s (captures %s %s)" % ( figure, dstString, dst, captures, figureDst ) )
       squares = self.moveFigureOnBoard( color, figure, dst, captures )
       l = len( squares )
       if l == 0 :
           raise BoardException( "no figure found" )
       elif l == 1 and ( figure != "P" or not captures ):
           figure = figure if figure != "P" else ""
           self.setSquare( src, " " )
           self.setSquare( dst, coloredFigure )
           return "%s%s%s" % ( figure, captureString, m[2:] )
       else :
           figure = figure if figure != "P" else ""
           srcResultString = ""
           if src[ 0 ] != dst[ 0 ] :
               srcResultString += str( unichr( ord( 'a' ) + src[ 0 ] - 1) )
           elif src[1 ] != dst[ 1 ] :
               srcResultString += str( unichr( ord( '1' ) + src[ 1 ] - 1 ) )
           return "%s%s%s%s" % ( figure, srcResultString, captureString, m[2:] )
       

   def transformListofAlgebraicMoveIntoPgn( self, moveListString, color ) :
       pgnMoves = ""
       moveList = moveListString.split()
       for m in moveList :
           print( "moveAlgebraic: %s" % ( m ) )
           pgnMove = self.moveAlgebraic( m, color )
           print( "movePgn: %s" % ( pgnMove ) )
           pgnMoves += " " + pgnMove
           color = "b" if color == "w" else "w"
       return pgnMoves 
       
 
class Move( object ) :
    def __init__( self, movenumber, whiteMove, blackMove ) :
        pass

##############################################################################################################    

class UCIEngine( object ) :
    # IGNORE_ANSWERS = [ "info currmove", "bestmove", "info depth", "info nodes" ]
    IGNORE_ANSWERS = []
    def __init__( self, pathToExecutable ) : 
       self.pathToExe = pathToExecutable
       self.init()
       self.positionString = "position startpos moves"

    def scanMultiPVLine( self, data ) :
        pass

    def filterUCIOutput( self ) :
        pass
        # we are only interested in "info .* .* score cp .* pv"

    def readUCIOutput( self ) :
        poll = select.poll()
        poll.register( self.enginePipe.stdout.fileno(), select.POLLIN )
        fileDescriptorList = poll.poll( 100 )
        data = None
        while len( fileDescriptorList ) > 0 and ( fileDescriptorList[ 0 ][ 1 ] &  select.POLLIN ) : 
            data = self.enginePipe.stdout.readline()
            printAnswer = True
            for ignorePrefix in self.IGNORE_ANSWERS : 
                if data.find( ignorePrefix ) != -1 :
                    printAnswer = False
                    break
            if printAnswer :
                print( data, end = "" )
            fileDescriptorList = poll.poll( 100 )
        return data
            
    def init( self ) :
        self.enginePipe = Popen( [ self.pathToExe ], stdout = PIPE, stdin = PIPE )
        sleep( 0.1 )
        print( "uci", file = self.enginePipe.stdin )
        self.readUCIOutput()

    def finish( self ) :
        print( "quit", file = self.enginePipe.stdin )
        self.enginePipe.terminate()
        self.enginePipe.wait()
        
    def nextMove( self, m ) :
        self.positionString = self.positionString + " " + m
        print()
        print( self.positionString )
        print()
        print( self.positionString, file = self.enginePipe.stdin )
        self.readUCIOutput()
        print( "go", file = self.enginePipe.stdin )
        sleep( 1 )
        self.readUCIOutput()
        print( "stop", file = self.enginePipe.stdin )
        sleep( 0.1 )
        self.readUCIOutput()

    def analyzeGame( self, game ) :
        board = Board()
        board.startPosition()
        blackMissing = False
        for move in game.moves :
            if blackMissing :
                raise BoardException( "White moves at %s after black has not moved", move.moveNumber )
            
            algebraicMove = board.movePgn( move.whiteMove, "w" )
            self.nextMove( algebraicMove )
            
            if move.blackMove : 
                algebraicMove = board.movePgn( move.blackMove, "b" )
                self.nextMove( algebraicMove )
            else :
                blackMissing = True

            

def testUCIEngine( game ) :
    UCI_ENGINE_PATH = "/home/ebayerle/temp/Critter-16a/critter-16a-64bit"
    # UCI_ENGINE_PATH = "/Users/ebayerle/Downloads/stockfish-7-mac/Mac/stockfish-7-64"
    engine = UCIEngine( UCI_ENGINE_PATH )
    engine.analyzeGame( game )
    # engine.nextMove( "e2e4" )
    # engine.nextMove( "g8f6" )
    engine.finish()

def testBoard(): 
    # b = Board()
    # b.readFen( b.STARTPOS_FEN )
    # b.print()
    # 
    # b.movePgn( "Nc3", "w" )
    # b.movePgn( "Nf3", "w" )
    # b.movePgn( "Nd4", "w" )
    # b.movePgn( "Ncb5", "w" )
    # b.movePgn( "e4", "w" )
    # b.movePgn( "f5", "b" )
    # b.movePgn( "Qh5", "w" )
    # # b.movePgn( "exf5", "w" )
    # b.print()
    # 
    # m = b.moveAlgebraic( "e4f5", "w" )
    # print( "%s -> %s" % ( "e4f5", m ) )
    # b.print()
    # 
    # m = b.moveAlgebraic( "h5f5", "w" )
    # print( "%s -> %s" % ( "h5e5", m ) )
    # b.print()
    # 
    # m = b.moveAlgebraic( "e1f1", "w" )
    # print( "%s -> %s" % ( "e1f1", m ) )
    # b.print()
    
    # print( "Position %s to %s" % ( "d2", b.positionStringToTupple( "d2" ) ) )
    # print( "Position %s to %s" % ( "2", b.positionStringToTupple( "2" ) ) )
    # print( "Position %s to %s" % ( "a", b.positionStringToTupple( "a" ) ) )

    b = Board()
    b.readFen( b.STARTPOS_FEN )
    b1 = Board( b )
    # b1.print()

    moveAlgebraicList = "d2d4 d7d5 c1f4 g8f6 g1f3 e7e6 e2e3 f8d6 b1c3 e8g8 f1d3 d6f4 e3f4 d8d6 d1d2 a7a6 e1g1 b8c6 a2a3 c8d7 h2h3 h7h6 a1e1"
    pgnVariation = b1.transformListofAlgebraicMoveIntoPgn( moveAlgebraicList, "w" )
    b1.print()
    b.print()
    print( "Algebraic: %s" % ( moveAlgebraicList ) )
    print( "PGN: %s" % ( pgnVariation ) )
    

def parsePgnFile( filename ) :
    parser = PgnParser( Scanner( filename ) )
    game = parser.game()
    game.print()
    return game


def testShallowCopy() :
    b = Board()
    b1 = Board( b )
    b.readFen( b.STARTPOS_FEN )
    b1.print()
    b.print()

if __name__ == '__main__':
    if len( argv ) >= 2:
        game = parsePgnFile( argv[ 1 ] )
    testUCIEngine( game )
    # testShallowCopy()
    # testBoard()
