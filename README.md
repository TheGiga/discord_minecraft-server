# Minecraft Server Manager Bot
Discord bot that lets you run dockerized minecraft servers.
*NOTE: You must host it yourself, for now at least.*

It is using [itzg/docker-minecraft-server](https://github.com/itzg/docker-minecraft-server).

## You can:
- [x] Configure server properties (inside of `/start` command)
- [x] Run multiple Java Edition versions. (I tested from 1.19.3 to 1.7.10)
- [x] Upload/Download world(s) to/from server.
- [x] Fully use server console in a discord text channel.

## You can't (but its planned ~~somewhat~~)
- [ ] Run multiple server(s) at once.
- [ ] Upload plugins
- [ ] Make `/start` templates.

## Configurable
You can configure most of the stuff, just change variables in `config.py` file to your desired ones.
There is more info on what's what in the file.

## Setting up:
1. Clone this repository by running `git clone https://github.com/TheGiga/discord_minecraft-server`
2. Create `.env` file and put your bot token here *(see .env.example)*
- See how to create the bot, get its token and invite to your server [here](https://guide.pycord.dev/getting-started/creating-your-first-bot)
3. Set up an HTTP server *(Optional, see [here](https://github.com/TheGiga/discord_minecraft-server#http-server))*
4. Configure `config.py`, you may need to change some settings. *(see [here](https://github.com/TheGiga/discord_minecraft-server#configurable))*
5. Install requirements by running `pip3 install -r requirements.txt`
6. Run the bot using `python3 main.py`
7. Start your server by running `/start` 


### HTTP Server
You need an HTTP server *(python http.server, or any other to your desire, bot just puts `.zip` files to specific path)* to download world(s) from server, because discord sucks and can't give enough file size limit for bigger wordls.

You can set up one by running:
- `python -m http.server <port>` in your directory. 
> Default port is 6969, It should be open if you want to access it outside of local network.

> Default directory is `/home/$USER/Public` (Linux) or `C:/Users/$USER/Public` (Windows). 

## Report any errors!
Make an Issue on GitHub if you are having trouble setting up/running bot.

*Bot was tested on 3 machines: 2 PC's and a Contabo server*
