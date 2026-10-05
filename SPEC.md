# Design
## Problem statement
Imagine you're implementing the backend for a messenger app. Users can be in conversations with one or more other users, send messages, and see which messages have been read.

Before you write any code, walk us through your design:

What data structures would you use for messages, timestamps, and metadata?
How would you track read receipts performantly?
What edge cases would you test for?
How would you debug and ship your code?

## clarify
* let's say we make a new groupchat with the same people, do we want that to reference the existing groupchat? like if i have a chat with bob and sarah and make a new chat with them, it should refernce the same chat, right? assume: yes
* for read receipts, i'm assuming that it's like snapchat where the read receipt will show who has viewd it. imessage doesn't evne show read receipts for groupchats, so jus ciorus. assumume: yes
* do care about the user not seeing messages befor ethey joined? because then we can have a "joined at" param in the partiipants set. assume: out of scope. don't worry about that. 


## data structures
* messages: dictionary with msg_id -> ordered list of messages (append only to retain proper order)
    * messages = "msg_id": {message_id, convo_id, sender_id, body, timestamp}
* timestamps: 
* metadata: 

i'm maybe not understanding what you mean by timestamps and metadata
but messages will incude timestamp within it and necessary metadata

you don't explicityl state it, but converstaions will be a dictionary mapping to convo_id and particpants set, messages list

and it'll be in that participants set that for each participatn we'll track "msg_id_last_read" along with convo_id and user_id


## interfaces
* get_conversations
* start_conversation
* get_participant(s)
* send_messages
* mark_read

## how to track read receipts performantly
i'm thinking of 2 options off the bat:
1. for every message, retain a set of partipants who have viewed it. but this seems inefficient, so i'm thinking a better solutiion is:
2. within set of participants in a conversation, also track the message_id of the most recent message they've seen. this is better because lets say tehre are 100 messages someone has to read, as htey read, instead of doign 100 updates/writes, are just keeping 1 "bookmark" for the most recent message viewed 

## edge cases:
* make sure we handle null and overloaded messages (must be < than 500 characters)
* security: someone who is not a participant in the conversation (a non member) cannot view or send messages
* make sure that viewing older messges doesn't push back your "bookmark"
* make sure in general that 2 operatiiions back to back don't break anyhting and thatn we handle null / wrong inputs for every method

## debug & plan
* if i find a bug in the code, i would write a test case to see that it fails. thenf ix the code, run the test again to amke sure it's green
* for existing testst aht fail, make sure it's the actual undrelying code's fault and not bc the test is erroneously written
* log erorrs
* roll out to small set of users so that rolling back is easy

## plan for building
step 1: 
set up basic get conversation, new converstaion, and retreiving participatns with tests
step 2: sending and receiving messages are handled + associated tests
step 3: implement "mark read" logic 
step 4: run all tests all together and give a summary + plan for next steps if i wanted to improve the application
