import discord
import openai
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
import os
import requests
from io import BytesIO
import json

load_dotenv('config.env')

discord_bot_token = os.getenv('DISCORD_BOT_TOKEN')
openai.api_key = os.getenv('OPENAI_API_KEY')

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', description="AI Bot", intents=intents)

last_five_prompts_and_answers = []

allow = True

@bot.command()
async def ask(ctx, *, question=None):
    """
    Ask general questions to the AI, or upload a file.
    """
    global last_five_prompts_and_answers

    # Check if there are attachments in the message
    if ctx.message.attachments:
        attachment = ctx.message.attachments[0]  # Get the first attachment
        if attachment.filename.endswith(('.txt', '.pdf', '.docx', '.py')):  # Check file type
            file_content = await attachment.read()  # Read the file content
            question = file_content.decode('utf-8')  # Decode to string if it's a text file
        else:
            await ctx.send("Unsupported file type.")
            return
    elif not question:
        await ctx.send("You need to ask a question or upload a text file after the !ask command.")
        return

    async with ctx.typing():
        try:
            # Read existing context from the file
            try:
                with open('context.txt', 'r') as file:
                    last_five_prompts_and_answers = json.load(file)
            except FileNotFoundError:
                # If the file doesn't exist yet, it's okay
                pass

            # Add the current question to the context (without an answer yet)
            last_five_prompts_and_answers.append({"role": "user", "content": question})
            if len(last_five_prompts_and_answers) > 6:
                last_five_prompts_and_answers.pop(0)

            # Send the prompt with the context to OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-4-1106-preview", 
                messages=last_five_prompts_and_answers
            )

            # Extract and send the message
            message = response['choices'][0]['message']['content']
            await asyncio.sleep(len(message) * 0.01)

            # Update the context with the new answer
            last_five_prompts_and_answers.append({"role": "assistant", "content": message})
            if len(last_five_prompts_and_answers) > 10:
                last_five_prompts_and_answers.pop(0)

            # Save the updated context to the file
            with open('context.txt', 'w') as file:
                json.dump(last_five_prompts_and_answers, file)

        except openai.error.OpenAIError as e:
            await ctx.send(f"An error occurred: {e}")
            return
        except Exception as e:
            await ctx.send(f"An unexpected error occurred: {e}")
            return

    await ctx.send(message)


@bot.command()
async def img(ctx, *, prompt):
    """
    Generate images with Dall-e 3
    """
    if allow == True:
        try:
            response = openai.images.create(model="dall-e-3", prompt=prompt, n=1, size="150x150")
            image_url = response['data'][0]['url']
            image_response = requests.get(image_url)
            await ctx.send(file=discord.File(BytesIO(image_response.content), "generated_image.png"))
        except Exception as e:
            await ctx.send(f"Error: {e}")
    else:
        await ctx.send(r"you can't because it's disabled")
        
@bot.command()
async def catgpt(ctx, *, catgpt_user_input=None):
    """
    Specify a cat you want, and I will generate it for you
    """
    if allow:  # Ensure 'allow' variable is defined somewhere in your code
        catgpt_input = "Generate a cat based on these parameters: " + catgpt_user_input
        try:
            # Generating images with DALL-E
            catgpt_response = openai.Image.create(
                prompt=catgpt_input, 
                n=1, 
                size="1024x1024"
            )
            # Assuming the response structure has a direct URL to the image
            catgpt_image_url = catgpt_response['data'][0]['url']
            catgpt_image_response = requests.get(catgpt_image_url)
            await ctx.send(file=discord.File(BytesIO(catgpt_image_response.content), "generated_catgpt_image.png"))
        except Exception as e:
            await ctx.send(f"Error: {e}")
    else:
        await ctx.send("You can't because it's disabled")

@ask.error
async def ask_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("You need to ask a question after the !ask command.")
    else:
        await ctx.send("An error occurred while processing your request.")

bot.run(discord_bot_token)