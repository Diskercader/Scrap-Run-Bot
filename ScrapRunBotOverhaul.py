#All of our imports as usual
import discord
from datetime import datetime, timezone, timedelta
import pytz
import math
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

#Create our Discord bot object to interact with API
client = discord.Client()

#Quick helper method to help with program arg creation
def readFullFile(fileName):
    file = open(fileName, mode='r')
    returnStr = file.read()
    file.close()
    return returnStr

# ========================================================
# = PROGRAM VARIABLES
# ========================================================

#Info that relates to the Scrap Run event itself
programArgs = dict.fromkeys(["maxBolts", "maxGangBolts", "numHours", "endTime", \
                             "boltsList", "quantitiesList", "rewardsList", \
                             "gangBoltsList", "gangQuantitiesList", "gangRewardsList"])
#Info for interacting with Discord API
serverComms = {
    "whiteListChannels": [720470055401291799, 314258703370944523, 782419338212147201, 636684529796382720],
                    #Bot-helpers (SP), #Bot-commands (Cats), #Scrap-run-bot-test, CATS main testing
    "whiteListAdmins": [299335413229944833, 260834727865483264],
                       #Diskercader,        Oops
    "whiteListPrefix": [".", "$", ".", "$"],
    "userList": []
}
#Securely load Tokens from another file
tokens: dict = json.loads(readFullFile('botKeys.json'))
#List of commands for user levels
userCommands = ["help", "maxbolts", "rewards", "sleepmax", "boltsmissed", "timeuntil", "gangmax", "gangrewards", "ping", "deepping", "update", "clear", "prime"]
adminCommands = ["ping", "deepping", "update", "clear", "prime"]
#Helpful variables / constants
PROGRAM_STATE = "CLEARED"
TIMEDELTA_ZERO = timedelta(0)

# ========================================================
# = ADMIN COMMANDS
# ========================================================

### Returns the ping with 2 decimal points
  # RETURN: str: The bot latency
def pingBotCommand():
    return f"Bong! Response time: {str(round(client.latency * 1000,2))}ms"

### Clears up memory after the event is over
  # RETURN: NoneType
def clearBotCommand():
    global programArgs, PROGRAM_STATE
    programArgs = {}.fromkeys(programArgs, None)
    serverComms["userList"] = []
    PROGRAM_STATE = "CLEARED"
    print("PROGRAM HAS BEEN CLEARED.")

### Gets the bot ready for an event soon
  # RETURN: NoneType
def primeBotCommand():
    global PROGRAM_STATE
    PROGRAM_STATE = "PRIMED"
    print("PROGRAM PRIMED FOR UPCOMING EVENT.")

### Connects to Google Sheets to populate program variables with event data
  # botLocation (str): Where the bot should find the SSH key depending where it's hosted
  # RETURN: NoneType
def updateBotCommand(botLocation):
    global programArgs, PROGRAM_STATE

    #Authenticate to access Google Sheets first
    scope = ['https://www.googleapis.com/auth/drive']
    laptopLocation = 'service_account.json'
    opcLocation = '/home/opc/DiscordBots/key.json'
    keyFileLoc = laptopLocation if botLocation == "laptop" else opcLocation
    key = ServiceAccountCredentials.from_json_keyfile_name(keyFileLoc)
    googleClient = gspread.authorize(key)

    #Open our Google Sheets with all the event data
    rewardsSheet = googleClient.open('ScrapRunData').sheet1

    #Populate our program with data from Google Sheets
    programArgs["boltsList"] = [int(x) for x in rewardsSheet.col_values(1)[1:]]
    programArgs["quantitiesList"] = [int(x) for x in rewardsSheet.col_values(2)[1:]]
    programArgs["rewardsList"] = rewardsSheet.col_values(3)[1:]
    programArgs["gangBoltsList"] = [int(x) for x in rewardsSheet.col_values(4)[1:]]
    programArgs["gangQuantitiesList"] = [int(x) for x in rewardsSheet.col_values(5)[1:]]
    programArgs["gangRewardsList"] = rewardsSheet.col_values(6)[1:]
    programArgs["maxBolts"] = int(rewardsSheet.col_values(7)[1])
    programArgs["maxGangBolts"] = int(rewardsSheet.col_values(8)[1])
    programArgs["numHours"] = int(rewardsSheet.col_values(9)[1])
    programArgs["endTime"] = pytz.utc.localize(datetime.strptime(rewardsSheet.col_values(10)[1], '%Y-%m-%d %H:%M:%S.%f'))

    PROGRAM_STATE = "UPDATED"
    print("PROGRAM VARIABLES UPDATED.")

### Looks for a State Change command & executes it if found
  # message (Message): The Discord Message object passed directly
  # RETURN: bool: Whether or not a State Change is executed
def executePotentialProgramStateCommand(message):
    keyword = message.content.split()[0][1::].lower()
    stateChangeExecuted = keyword in adminCommands[2:]
    if keyword == "clear":
        clearBotCommand()
    elif keyword == "prime":
        primeBotCommand()
    elif keyword == "update":
        try:
            botLocation = message.content.split()[1]
        except:
            botLocation = "opc"
        updateBotCommand(botLocation)
    return stateChangeExecuted

# ========================================================
# = UTILITY METHODS
# ========================================================

### Checks whether the user has used a valid command
  # userMessage (String): The message that the user puts in the channel
  # channelID (int): The Discord server ID
  # userID (int): the Discord user ID
  # RETURN: boolean: Whether or not a valid command has been used
def checkValidCommand(userMessage, channelID, userID):
    keyword = userMessage.split()[0][1::].lower()
    prefix = userMessage[:1:]
    adminPerms = True if keyword not in adminCommands else userID in serverComms["whiteListAdmins"]
    validCommand = keyword in userCommands and \
                   channelID in serverComms["whiteListChannels"] and \
                   prefix == serverComms["whiteListPrefix"][serverComms["whiteListChannels"].index(channelID)] and \
                   adminPerms
    return validCommand

### Verifies whether all of the bools passed in evaluate to True
  # *boolCondition (tuple): A tuple of potential bool conditions
  # RETURN: boolean: Whether every command passed in evaluates to True
def verifyAllConditionsTrue(*boolCondition):
    returnBool = True
    for condition in boolCondition:
        if not condition: returnBool = False
    return returnBool

### Rounds a number down to the nearest 10
  # inputNumber (int): The number to be rounded down
  # base (int): The multiple you want it rounded down by
  # RETURN: int: The number rounded down to the nearest 10
def roundDown(inputNumber, base=10):
    return base * round(inputNumber/base)

### Prints an Argument Length Error
  # RETURN: NoneType
def printArgumentLengthError():
    return "**Error:** Received either too many or too few arguments. Please check thar your inputs follow guidelines: "

### Prints an Argument Datatype Error
  # RETURN: NoneType
def printDataTypeError():
    return "**Error:** 1 or more inputs have the wrong datatype. Please ensure your arguments have the correct datatype."

### Prints an Argument Logic Error
  # RETURN: NoneType
def printArgumentLogicError():
    return "**Error:** One or more input is either negative or above the expected range. Please double check that your inputs follow guidelines."

# ========================================================
# = BOT COMMAND SECONDARY METHODS
# ========================================================

### Tracks the number of unique users of the bot
  # userID (int): The Discord user ID
  # RETURN: NoneType
def searchNewUser(userID):
    if userID not in serverComms["userList"]:
        serverComms["userList"].append(userID)
        print(f"New user! {userID} is user #{len(serverComms['userList'])}")

### Calculates how many bolts a player can earn in standard SR
  # currentBolts (int): The number of bolt the player has already earned
  # multiplier (int): The multiplier that the player has
  # minutes (int): The number of minutes remaining in the event
  # RETURN: int: The max bolts that someone could gain from the event
def calculateBoltsRegular(currentBolts, multiplier, minutes):
    unearnedBolts = (minutes // 10) * multiplier
    maxPotentialBolts = currentBolts + unearnedBolts
    return maxPotentialBolts

### Calculates how many bolts you can earn with hours of sleep per night
  # multiplier (int): The multiplier that the player has
  # hoursOfSleep (int): How many hours the user will sleep each night
  # RETURN: int: The max bolts you could earn given sleep each night
def calculateBoltsSleep(multiplier, hoursOfSleep):
    boltsPerHour = 6 * multiplier
    # This accounts for 4 periods of sleep in the event- <sleepLoss per day> * <number of days>
    sleepLoss = 0 if hoursOfSleep < 2.3 else ((hoursOfSleep * boltsPerHour) - (14 * multiplier)) * (programArgs["numHours"] / 24)
    maxBoltsPossible = 13 + (boltsPerHour * programArgs["numHours"]) - sleepLoss
    return maxBoltsPossible

### Calculates how many of what rewards are gained up to a certain number of bolts
  # boltsGoal (int): The number of bolts to calculate rewards up to
  # RETURN: dict[str, int]: The rewards & quantities earned
def calculateEarnedRegular(boltsGoal):
    goalPartAndQuantity: dict[str, int] = {}

    for potentialReward in range(len(programArgs["boltsList"])):
        if programArgs["boltsList"][potentialReward] <= boltsGoal:
            #These variables aren't strictly necessary but nice QOL
            reward = programArgs["rewardsList"][potentialReward]
            rewardQuantity = programArgs["quantitiesList"][potentialReward]
            if reward not in goalPartAndQuantity:
                goalPartAndQuantity[reward] = rewardQuantity
            else:
                goalPartAndQuantity[reward] += rewardQuantity

    return goalPartAndQuantity

### Format the rewards you can get, and have already gotten, from this event
  # boltsEarned (int): How many bolts you've already earned
  # boltsPossible (int): How many bolts you could possibly gain
  # RETURN: str: A list of rewards & quantities you can / have earned from the event
def calculateRewardsRegular(boltsEarned, boltsPossible):
    returnStr = "```"
    PossiblePartAndQuantity = calculateEarnedRegular(boltsPossible)
    earnedPartAndQuantity = calculateEarnedRegular(boltsEarned)

    for potentialReward in PossiblePartAndQuantity:
        returnStr += f"\n{PossiblePartAndQuantity[potentialReward]} {potentialReward}"
        if potentialReward in earnedPartAndQuantity:
            returnStr += f" - {earnedPartAndQuantity[potentialReward]} earned"
    
    return returnStr + '```'

### Calculates how many of what gang milestones are gained up to a certain number of bolts
  # boltsGoal (int): The number of bolts to calculate gang milestones up to
  # RETURN: dict[str, int]: The rewards & quantities earned
def calculateEarnedGang(boltsGoal):
    goalPartAndQuantity: dict[str, int] = {}

    for potentialReward in range(len(programArgs["gangBoltsList"])):
        if programArgs["gangBoltsList"][potentialReward] <= boltsGoal:
            #These variables aren't strictly necessary but nice QOL
            reward = programArgs["gangRewardsList"][potentialReward]
            rewardQuantity = programArgs["gangQuantitiesList"][potentialReward]
            if reward not in goalPartAndQuantity:
                goalPartAndQuantity[reward] = rewardQuantity
            else:
                goalPartAndQuantity[reward] += rewardQuantity

    return goalPartAndQuantity

### Format the gang milestones you can get, and have already gotten, from this event
  # boltsEarned (int): How many gang milestones you've already earned
  # boltsPossible (int); How many bolts your gang could possibly gain
  # RETURN: str: A list of rewards & quantities your gang can / has earned from the event
def calculateRewardsGang(boltsEarned, boltsPossible):
    returnStr = "```"
    PossiblePartAndQuantity = calculateEarnedGang(boltsPossible)
    earnedPartAndQuantity = calculateEarnedGang(boltsEarned)
    print(f"Possible: {PossiblePartAndQuantity}")
    print(f"Earned: {earnedPartAndQuantity}")

    for potentialReward in PossiblePartAndQuantity:
        returnStr += f"\n{PossiblePartAndQuantity[potentialReward]} {potentialReward}"
        if potentialReward in earnedPartAndQuantity:
            returnStr += f" - {earnedPartAndQuantity[potentialReward]} earned"
    
    return returnStr + '```'

### Independent method to calculate Premium rewards in standard SR
  # RETURN: str: A formatted list of rewards gained by purchasing a multiplier
def premiumRewardsWrapper():
    f2pMax = 6 * programArgs["numHours"] + 13
    returnStr = f"Additional rewards with multiplier ({f2pMax + 1}-{programArgs['maxBolts']} bolts):\n```"
    f2pPartsAndQuantities = calculateEarnedRegular(f2pMax)
    allPartsAndQuantities = calculateEarnedRegular(programArgs["maxBolts"])

    #Sick ass Dictionary comprehension
    premiumPartsAndQuantities = {reward: allPartsAndQuantities[reward] - f2pPartsAndQuantities.get(reward, 0) for reward in allPartsAndQuantities\
    if f2pPartsAndQuantities.get(reward, 0) != allPartsAndQuantities[reward]}
    #Now just add our Premium dict contents to the user message
    for reward in premiumPartsAndQuantities:
        returnStr += f"{premiumPartsAndQuantities[reward]} {reward}\n"
    return returnStr + "```"

# ========================================================
# = BOT COMMAND PRIMARY METHODS
# ========================================================

### Help command to be DM'd to users
  # prefix (str): The server's prefix
  # RETURN: str: The help message, formatted for the source server
def helpBotCommand(prefix):
    return f"""**Additional documentation is as follows:**

``{prefix}maxbolts bolts multiplier``
**Purpose**: Calculate the maximum # of bolts you can earn before the end of the event.
`bolts`: The number of bolts you currently have.
`multiplier`: The multiplier you have.

``{prefix}rewards bolts``
**Purpose**: Return the list of rewards up to a certain # of bolts.
`bolts`: The number of bolts you want rewards for. Argument can be *replaced* with `max`, `f2p`, or `premium` for additional functionality.

``{prefix}sleepmax multiplier sleep``
**Purpose**: Calculates the maximum # of bolts you can earn with a certain amount of sleep each night.
`multiplier`: The multiplier you have.
`sleep`: The number of hours you will sleep each night. This can be a decimal value.

``{prefix}boltsmissed bolts multiplier``
**Purpose**: Calculates the number of bolts you've missed throughout the event.
`bolts`: Your current number of bolts.
`multiplier`: The multiplier you have.

``{prefix}gangmax bolts members``
**Purpose**: Calculate how many bolts your gang can earn total.
`bolts`: The current # of combined bolts.
`members`: How many members your gang has.
*This is a rough estimation and will likely only be an approximation of your final result.*

``{prefix}gangrewards bolts``
**Purpose**: Calculate the rewards your gang will earn
`bolts`: The # of bolts you expect to earn. Can be replaced with `max` for additional functionality."""

### Maxbolts command & associated logic
  # currentTime (datetime): The current time in UTC
  # message (str): The Discord message.content for ease of use
  # prefix (str): The server's prefix
  # RETURN: str: The String to be sent to the channel for the user
def maxboltsBotCommand(currentTime, message, prefix):
    minutesRemaining = int((programArgs["endTime"] - currentTime).total_seconds() // 60)
    splitMessage = message.split()

    #Check to ensure we have the right number of arguments
    if len(splitMessage) != 3:
        return printArgumentLengthError() + f"``{prefix}maxbolts [# of bolts] [multiplier amount]``. Type `{prefix}help` for more info."
    #Add values, being mindful of potential datatype errors
    try:
        bolts = int(splitMessage[1])
        multiplier = int(splitMessage[2])
    except ValueError:
        return printDataTypeError()
    #Verify that the arguments make sense logically
    if not verifyAllConditionsTrue(bolts >= 0, bolts < programArgs["maxBolts"], multiplier > 0, multiplier < 4):
        return printArgumentLogicError()

    #Proceed fearlessly with our main method logic
    maxPotentialBolts = calculateBoltsRegular(bolts, multiplier, minutesRemaining)
    #Check to see how much time they have remaining
    surplusMinutes, surplusHours = 0, 0
    if maxPotentialBolts > programArgs["maxBolts"]:
        surplusMinutes = roundDown(((maxPotentialBolts-programArgs["maxBolts"]) / multiplier) * 10)
        surplusHours = surplusMinutes // 60
        surplusMinutes = surplusMinutes % 60
        maxPotentialBolts = programArgs["maxBolts"]
    #Get the rewards list & start creating our response
    botResponse = f"You can earn **{maxPotentialBolts} bolts** this event. "
    if maxPotentialBolts > programArgs["boltsList"][0]:
        botResponse += "Please see your rewards list below."
        botResponse += calculateRewardsRegular(bolts, maxPotentialBolts)
        if surplusMinutes + surplusHours != 0:
            botResponse += f"You will finish the event with **{str(surplusHours)} hours, {str(surplusMinutes)} minutes** remaining."
    else:
        #I'll eat my shorts if someone triggers this & shows it to me
        botResponse += "Unfortunately, you cannot earn any rewards this event!"
    return botResponse

### Rewards command & associated logic
  # message (str): The Discord message.content for ease of use
  # prefix (str); The server's prefix
  # RETURN: str: The String to be sent to the channel for the user
def rewardsBotCommand(message, prefix):
    splitMessage = message.split()

    #Check to ensure we have the right number of arguments
    if len(splitMessage) != 2:
        return printArgumentLengthError() + f"``{prefix}rewards [# of bolts]``. Type `{prefix}help` for more info."
    #We have to have a whole separate process for "rewards premium".
    if splitMessage[1] == "premium":
        return premiumRewardsWrapper()
    #Add values, being mindful of potential datatype errors
    try:
        bolts = programArgs["maxBolts"] if splitMessage[1] == "max" else \
                ((6 * programArgs["numHours"] + 13) if splitMessage[1] == "f2p" else \
                    int(splitMessage[1]))
    except ValueError:
        return printDataTypeError()
    #Verify that the arguments make sense logically
    if not verifyAllConditionsTrue(bolts >= 0, bolts <= programArgs["maxBolts"]):
        return printArgumentLogicError()

    #Proceed fearlessly with our main method logic
    if bolts < programArgs["boltsList"][0]:
        return f"**No rewards earned** at this level. The first reward is at {programArgs['boltsList'][0]} bolts."
    else:
        botResponse = f"Maximum rewards for {bolts} bolts:\n```"
        rewards = calculateEarnedRegular(bolts)
        for reward in rewards:
            botResponse += f"{rewards[reward]} {reward}\n"
        return botResponse + "```"

### Sleepmax command & associated logic
  # message (str): The Discord message.content for ease of use
  # prefix (str): The server's prefix
  # RETURN: str: The String to be sent to the channel for the user
def sleepmaxBotCommand(message, prefix):
    splitMessage = message.split()

    #Check to ensure we have the right number of arguments
    if len(splitMessage) != 3:
        return printArgumentLengthError() + f"``{prefix}sleepmax [multiplier amount] [hours of sleep per night]``. Type `{prefix}help` for more info."
    #Add values, being mindful of potential datatype errors
    try:
        multiplier = int(splitMessage[1])
        hoursOfSleep = float(splitMessage[2])
    except ValueError:
        return printDataTypeError()
    #Verify that the arguments make sense logically
    if not verifyAllConditionsTrue(multiplier > 0, multiplier < 4, hoursOfSleep >= 0, hoursOfSleep < 24):
        return printArgumentLogicError()
    
    #Proceed fearlessly with our main method logic
    maxPotentialBolts = calculateBoltsSleep(multiplier, hoursOfSleep)
    surplusMinutes, surplusHours = 0, 0
    if maxPotentialBolts > programArgs["maxBolts"]:
        surplusMinutes = roundDown(((maxPotentialBolts-programArgs["maxBolts"]) / multiplier) * 10)
        surplusHours = surplusMinutes // 60
        surplusMinutes = surplusMinutes % 60
        maxPotentialBolts = programArgs["maxBolts"]
    #Get the rewards list & start creating our response
    botResponse = f"You can earn **{int(maxPotentialBolts)} bolts** this event with {hoursOfSleep} hours of sleep. "
    if maxPotentialBolts > programArgs["boltsList"][0]:
        botResponse += "Please see your rewards list below.```"
        rewards = calculateEarnedRegular(maxPotentialBolts)
        for reward in rewards:
            botResponse += f"{rewards[reward]} {reward}\n"
        botResponse += "```"
        if surplusMinutes + surplusHours != 0:
            botResponse += f"You can finish the event with roughly **{str(surplusHours)} hours, {str(surplusMinutes)} minutes** remaining."
    else:
        #I don't know if this can be triggered, but better safe than sorry
        botResponse += "Unfortunately, you cannot earn any rewards this event!"
    return botResponse

### Boltsmissed command & associated logic
  # currentTime (datetime): The current time in UTC
  # message (str): The Discord message.content for ease of use
  # prefix (str): The server's prefix
  # RETURN: str: The String to be sent to the channel for the user
def boltsmissedBotCommand(currentTime, message, prefix):
    minutesRemaining = int((programArgs["endTime"] - currentTime).total_seconds() // 60)
    splitMessage = message.split()

    #Check to ensure we have the right number of arguments
    if len(splitMessage) != 3:
        return printArgumentLengthError() + f"``{prefix}boltsmissed [# of bolts] [multiplier amount]``. Type `{prefix}help` for more info."
    #Add values, being mindful of potential datatype errors
    try:
        bolts = int(splitMessage[1])
        multiplier = float(splitMessage[2])
    except ValueError:
        return printDataTypeError()
    #Verify that the arguments make sense logically
    if not verifyAllConditionsTrue(bolts >= 0, bolts < programArgs["maxBolts"], multiplier > 0, multiplier < 4):
        return printArgumentLogicError()
    
    #Proceed fearlessly with our main method logic
    minutesPassed = (programArgs["numHours"] * 60) - minutesRemaining
    boltsPossible = ((minutesPassed // 10) * multiplier) + (14 * multiplier)
    return f"You have earned **{str(bolts)} bolts** out of a possible **{str(int(boltsPossible))} total.**"

### Gangmax command & associated logic
  # currentTime (datetime): The current time in UTC
  # message (str): The Discord message.content for ease of use
  # prefix (str): The server's prefix
  # RETURN: str: The String to be sent to the channel for the user
def gangmaxBotCommand(currentTime, message, prefix):
    minutesRemaining = int((programArgs["endTime"] - currentTime).total_seconds() // 60)
    splitMessage = message.split()

    #Check to ensure we have the right number of arguments
    if len(splitMessage) != 3:
        return printArgumentLengthError() + f"``" + prefix + "gangmax [# of bolts] [# of members]``. Type `" + prefix + "help` for more info."
    #Add values, being mindful of potential datatype errors
    try:
        bolts = int(splitMessage[1])
        members = float(splitMessage[2])
    except ValueError:
        return printDataTypeError()
    #Verify that the arguments make sense logically
    if not verifyAllConditionsTrue(bolts >= 0, bolts < programArgs["maxGangBolts"], members > 0, members < 26):
        return printArgumentLogicError()
    
    #Proceed fearlessly with our main method logic
    minutesPassed = (programArgs["numHours"] * 60) - minutesRemaining
    boltsPerTick = (bolts - (14 * members)) / (minutesPassed / 10)
    gangBoltMax = math.floor(boltsPerTick * (programArgs["numHours"] * 6) + (14 * members))
    if gangBoltMax < 0:
        returnStr = "Average bolts so far resulted in a negative bolts per minute prediction- please try again later!"
    else:
        if gangBoltMax > programArgs["maxGangBolts"]: gangBoltMax = programArgs["maxGangBolts"]
        returnStr = f"Your gang will earn **{gangBoltMax} bolts** by the end of the event."
        if gangBoltMax > programArgs["gangBoltsList"][0]:
            returnStr += " Rewards list is as follows: "
            returnStr += calculateRewardsGang(bolts, gangBoltMax)
            returnStr += "\n*Please note that this is just a educated prediction based on prior performance. I am not a perfect number, and will **overestimate** more than I **underestimate**.*"
        else:
            returnStr += f"\n**No rewards earned** at this level. The first reward is at {programArgs['gangBoltsList'][0]} bolts."
    return returnStr

### Gangrewards command & associated logic
  # currentTime (datetime): The current time in UTC
  # message (str): The Discord message.content for ease of use
  # prefix (str): The server's prefix
  # RETURN: str: The String to be sent to the channel for the user
def gangrewardsBotCommand(message, prefix):
    splitMessage = message.split()

    #Check to ensure we have the right number of arguments
    if len(splitMessage) != 2:
        return printArgumentLengthError() + f"``{prefix}rewards [# of bolts]``. Type `{prefix}help` for more info."
    #Add values, being mindful of potential datatype errors
    try:
        bolts = programArgs["maxGangBolts"] if splitMessage[1] == "max" else int(splitMessage[1])
    except ValueError:
        return printDataTypeError()
    #Verify that the arguments make sense logically
    if not verifyAllConditionsTrue(bolts >= 0, bolts <= programArgs["maxGangBolts"]):
        return printArgumentLogicError()
    
    #Proceed fearlessly with our main method logic
    if bolts < programArgs["gangBoltsList"][0]:
        return f"**No rewards earned** at this level. The first reward is at {programArgs['gangBoltsList'][0]} bolts."
    else:
        botResponse = f"Maximum rewards for {bolts} bolts:\n```"
        rewards = calculateEarnedGang(bolts)
        for reward in rewards:
            botResponse += f"{rewards[reward]} {reward}\n"
        return botResponse + "```"

# ========================================================
# = DISCORD API STARTUP EVENT
# ========================================================

@client.event
async def on_ready():
    print('Bot online - awaiting setup process')

# ========================================================
# = DISCORD API MESSAGE EVENT
# ========================================================

@client.event
async def on_message(message):
    
    #Ensure the bot doesn't respond to itself
    if message.author == client.user:
        return
    
    #Ensure the bot ignores anything that's not a valid command
    #This can be other conversations, another bot's command etc
    if not checkValidCommand(message.content, message.channel.id, message.author.id):
        return
    
    #Check to execute a State Change regardless of current State, and return if one is executed
    if executePotentialProgramStateCommand(message): return

    #Special case for checking ping regardless of case
    if message.content[1:] == "deepping":
        await message.channel.send(pingBotCommand())
        return

    #If PROGRAM_STATE is CLEARED, don't send any messages (basically bot offline)
    if PROGRAM_STATE == "CLEARED":
        return

    #If PROGRAM_STATE is PRIMED, just return a basic temporary message
    if PROGRAM_STATE == "PRIMED":
        await message.channel.send("The bot will be online soon! Expect rewards to be entered between 10:00-12:00 UTC")
        return

    #Automatically CLEAR if a command is attempted after the endtime
    currentTime = datetime.now(timezone.utc).replace(tzinfo=pytz.UTC)
    if currentTime - programArgs["endTime"] > TIMEDELTA_ZERO:
        clearBotCommand()
        return

    #Once it reaches this point, we know everythging is good to go
    minutesRemaining = int((programArgs["endTime"] - currentTime).total_seconds() // 60)
    
    keyword = message.content.split()[0][1::].lower()
    prefix = message.content[:1:]

    #Search for & execute the proper command
    if keyword == "help":
        botResponse = helpBotCommand(prefix)
        await message.author.send(botResponse)
        return
    elif keyword == "maxbolts":
        botResponse = maxboltsBotCommand(currentTime, message.content, prefix)
    elif keyword == "rewards":
        botResponse = rewardsBotCommand(message.content, prefix)
    elif keyword == "sleepmax":
        botResponse = sleepmaxBotCommand(message.content, prefix)
    elif keyword == "boltsmissed":
        botResponse = boltsmissedBotCommand(currentTime, message.content, prefix)
    elif keyword == "gangmax":
        botResponse = gangmaxBotCommand(currentTime, message.content, prefix)
    elif keyword == "gangrewards":
        botResponse = gangrewardsBotCommand(message.content, prefix)
    elif keyword == "ping":
        botResponse = pingBotCommand()

    searchNewUser(message.author.id)
    await message.channel.send(botResponse)

client.run(tokens["REAL_TOKEN"])