* Stochastic variant of chess
* See Substack (https://posev.substack.com/) for details. 
* Check you have installed the required packages. All good citizens should have numpy and pandas already, but you might need to install pygame. 

__PLAYING THE GAME__
* Run flipper_chess.py.
* When you open it will ask for who you want to play in each position (bot or computer) and to set the bot difficulty. 
* Don't expect too much from the bots - this is all written in python so it's rather low-performance. 
* Move by clicking on pieces then the square you want to move them to. Possible destination squares are shaded in lilac.
* To unselect a piece, click on somewhere that is not a possible move. 
* At the end, or any point during the game, you can save and quit. This saves to a csv in the "tapes" folder, the filename being the date and time of the game's end.

__REVIEWING GAMES__
* Edit game_viewer.py so "filename" is the name of the game csv you want to review.
* Run game_viewer.py.
* Buttons do as follows: right arrow and space move forward a move, left arrow goes back a move, up arrow goes to the start of the game, and down arrow to the end. Pressing "s" swaps the players around, so you can switch between black's and white's perspectives. And "q" quits the game. 
