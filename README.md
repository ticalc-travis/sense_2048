# sense\_2048

This is yet another clone of [Gabriele Cirulli's 2048](https://github.com/gabrielecirulli/2048) for the Astro Pi Sense HAT board (the one with the joystick and 8×8 LED array).
It uses the Sense HAT joystick for input and the LED array for output, using different colors to represent the tile numbers.
I developed and tested it with CPython 3.7 on the Raspberry Pi 4B; I have no idea how well it performs on the other Pi models.

Features include:

* Simple animation effects
* Scoring
* Multi-level undo \[perhaps overkill, but I thought it would be nice for practicing the game and experimenting with a strategy :-) \]

I made it for fun to try out the Sense HAT hardware and also as practice for code design and documentation. I don't know whether I've done a good job of that, but perhaps someone out there will find the code of some kind of educational or entertainment value.

## Running and playing

To run the game, place the **sense\_2048.py** script on a Pi with the Sense HAT installed, open a terminal, and go to the directory where the script is and launch it with Python 3 in the usual way:

    $ python3 ./sense_2048.py

Some instructions will appear on the console; the gameplay itself happens on the HAT.

To try out the game with the Sense HAT emulator instead of the physical hardware, open **sense\_2048.py** in a text editor and change the line that reads:

    from sense_hat import sense_hat

to:

    from sense_emu import sense_hat

The tile colors are as follows:

    2: white
    4: yellow
    8: orange
    16: red
    32: magenta
    64: purple
    128: deep blue
    256: light blue
    512: cyan
    1024: green
    2048: dark green

    4096*: dark cyan
    8192*: dark blue
    16384*: dark magenta
    32768*: dark red
    65536*: amber
    131072*: gray

\* If you achieve the 2048 tile, you are allowed to continue playing until you run out of moves; these tiles are thus theoretically possible.

## Hacking

There are a few things in the source code that you may find interesting to play around with.

The TILE_COLORS definition holds the RGB values of each tile value.
Edit this if you want to create your own tile color scheme.

The Board class definition's \_\_init\_\_ method defines parameters for the board size and the list of possible new tiles that can show up each turn.
You can change the board size's dimensions to one of the following: 2×2, 2×4 (and vice-versa), 4×4, 4×8 (and vice-versa), and 8×8.
The Board logic can technically handle arbitrary dimensions, but the UI graphics code will fail if the dimensions are not an integer divisor of 8.

The UI class has definitions that allow for changing the number of undo operations permitted, the speed of animation, and the amount of time for holding down the joystick middle button to detect the undo command.

## Experimental branches

I considered a couple of other features for this game that seemed cool on paper, but didn't seem so hot when I implemented them.
I removed them from the main branch but have included them in the GitHub repository as alternate branches in case anyone is curious or wants to fool around with them.
Note that these branches are snapshots of the program in earlier stages of development, so features and bug fixes I added afterward are absent.

### tilt\_sensor\_test and tilt\_sensing

These branches were an attempt to use the accelerometers to allow playing the game by tilting the Sense HAT to shift the tiles.
It technically works, but response time is a bit slow (as making it quicker makes it prone to false readings resulting in unintended moves), and I found the game overall somewhat tedious playing this way.
Moving the same direction more than once requires tipping the HAT once, leveling it for a moment, then tipping it again.
And I found that sometimes I tipped the HAT accidentally when holding it, resulting in an unwanted move.
So I kind of gave up on the idea.

### color_animations

When defining the colors for the tiles, I found it a bit challenging coming up with enough colors that were distinct and easy to differentiate.
I thought that giving tiles 2048 and higher an animated “pulsing” effect would add visual appeal and make it easier to tell the higher tiles apart from the lower ones.
When I implemented it, though, I felt the effect didn't help that much and was in fact a bit distracting.
