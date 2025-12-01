## 11/30/2025 5:27 PM ##

This devlog is going to track my thoughts and ideas for this project. This project involves b trees and the allocation of nodes in memory. The project gives a specific layout of how data is supposed to stored in the index file which is our container. 
In addition, I think the most difficult part of the project will be ensuring the b tree is maintaing its propoerty while keeping track of the connections between the different nodes. 

I am planning on first developing the basic creation of the index file and ensuring the format is how I want. Only after this is done, will I start on the CLI functionality for the different commands. Before I start coding, I am going to look into using different hex editors to view the index file.
This will help a lot with debugging as I progress. Next, I will organize the different componenets of the index file and make each componenet its own class. After I do this, I will figure out the next phase that I want to pursue in developing this program.

I realized that before the components, I need to do the check for big endian and handle it in the appropiate scenarios. In addition, I realized I need to make a class for the node that will contain all the attributes for the node.


## 11/30/2025 6:29 PM ##

I have started to implemnt the different componenets of the index file. I initally ran into the poroblem of understanding how values are organized in the format of the index file, but I think I have a better understanding now. In addition, I struggled to figure out the cases and checks for the big endian condition, but once again I think I have covered my bases. I have finished the header, and next session I am going to work on the node class. However, I will only learn if its correct once I get to working on the main method, where I can start with a basic flow to test what I have. Overall, I would say that I accomplished my goal for this session even though I did not finish as I better understand the scope of the project. In addition, I also understand more on how to use python to manipulate the bytes based on the section of output. Next session, I am going to continue to work on the Node path and hopefuly flesh out enough of the program so that I can test. Final note, I am working in a seperate branch call "dev".

## 12/1/2025 8:32 AM

After thinking about the project, I realized the node class needs to be more in depth than the header class as it has to store B-Tree information. In addition, I need to make sure I account for the sequence and size of the different sections within the node class. This session, my plan is to complete the node class and start on the different functions I will need to update node information. I need to make sure that the information is not being written into the incorrect spcaes and that the byte constraints are still being maintained as changes are made to the index file. I think to do this I am going to use loops within the node class to make sure the constraints of the different sections are being maintained. After I complete this, then I will flesh out a main method so that I can test the basic functionality of this program before I move on to the CLI commands.
