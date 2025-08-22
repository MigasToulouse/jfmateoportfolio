"""
Interactive Pokemon Catch Rate Calculator using Dash
For Pokemon Let's Go.
"""

#%% Library imports
import os
from random import choice, randint
import json
from io import BytesIO
import pandas as pd
from dash import Dash, Input, Output, callback, dcc, html, ctx
from PIL import Image
import requests
import numpy as np


#%% Database loading and configuration
DATASOURCES_PATH = os.path.join(os.getcwd(), r"resources")
DATABASE_PATH = os.path.join(DATASOURCES_PATH, r"pokemonletsgo_db.json")
UTILS_PATH = os.path.join(DATASOURCES_PATH, r"utils.json")

with open(DATABASE_PATH, "r", encoding="utf-8") as database,\
     open(UTILS_PATH, "r", encoding="utf-8") as utils:
    pokemon_db = json.load(database)
    utils_json = json.load(utils)

pokemon_dict = pokemon_db["pokemon"]
ballrate_dict = pokemon_db["ball_rate"]
technique_dict = pokemon_db["technique"]
berry_dict = pokemon_db["berry"]
pokemonchain_dict = pokemon_db["letsgochain"]

# Global variables
chaintext = html.Td("No chain", style={"font-weight": "normal"})
INIT_STATE = True

# Get the game logo
LOGO_URL = "https://archives.bulbagarden.net/media/upload/thumb/8/8b/Pok%C3%A9mon_Lets_Go_Eevee_Logo.png/800px-Pok%C3%A9mon_Lets_Go_Eevee_Logo.png?20180530032955"
response = requests.get(LOGO_URL, timeout=5)
game_logo = Image.open(BytesIO(response.content))


#%% Functions
def catch_pokemon(pokemon: str, combat_power: int, ball: str, berry: str) -> list:
    """
    Function handler to calculate the possible catch rates of a pokemon based on:
    - The pokemon species
    - CP
    - Ball type
    - Berry type
    For Pokemon Let's Go.

    Returns:
        A list of catch rates for each technique.
    """

    def catchrate_calc(technique: str) -> float:
        """
        Function to calculate the catch rate of a pokemon based on:
        - The pokemon species
        - CP
        - Ball type
        - Tecnique
        - Berry type
        For Pokemon Let's Go.

        Returns:
            A float of the catch rate.
        """
        times_caught = min(100, pokemon_dict[pokemon]["times_caught"])

        a = (1.25
            * np.pow( pokemon_dict[pokemon]["catch_rate"],(1 / 1.85) )
            * np.pow( (10000 / ((100 - times_caught) / 100 * combat_power + 1)), (1 / 4) )
            * np.pow( ballrate_dict[ball], (3 / 2) )
            * np.pow( (technique_dict[technique] * berry_dict[berry]), (1 / 2) )
        )

        # a = (
        #     1.25 * pokemon_dict[pokemon]["catch_rate"] ** (1 / 1.85)
        #     * (10000 / ((100 - times_caught) / 100 * combat_power + 1)) ** (1 / 4)
        #     * ballrate_dict[ball] ** (3 / 2)
        #     * (technique_dict[technique] * berry_dict[berry]) ** (1 / 2)
        # )

        # print(f"a: {a}")
        # b = 65535 / np.pow(a, (5 / 16))
        b = 65535 / np.pow(255 / a, (1 / 5.33))
        # print(f"b: {b}")
        catch_rate = (b / 65535) * 100
        # print(f"Catch rate: {(catch_rate)}")
        catch_rate = min(100, catch_rate)

        return round(catch_rate, 2)

    # Check if the pokemon, ball, technique, and berry are valid
    if pokemon not in pokemon_dict:
        print("Pokemon not found")
        return None
    if ball not in ballrate_dict:
        print("Ball not found")
        return None
    if berry not in berry_dict:
        print("Berry not found")
        return None

    # Calculate the catch rate
    return pd.DataFrame(
                [[technique, catchrate_calc(technique)] for technique in technique_dict],
                columns=["Technique", "Catch Rate"]
                )

def catchring_color(catch_rate: float) -> str:
    """
    Function to determine the color of the catch ring based on the catch rate.
    # Ring color
    # CR<70%: red
    # 70<=CR<75%: orange
    # 75<=CR<80%: yellow
    # 80<=CR: green
    """
    color_thresholds = {
        "orange": 70.0,
        "yellow": 75.0,
        "green": 80.0,
    }
    if catch_rate < color_thresholds["orange"]:
        return "red"
    if color_thresholds["orange"] <= catch_rate < color_thresholds["yellow"]:
        return "orange"
    if color_thresholds["yellow"] <= catch_rate < color_thresholds["green"]:
        return "gold"
    return "green"

def get_sprite(pokemon: str, shiny: bool = False) -> str:
    """
    Function to get the sprite URL of a pokemon.
    """
    if shiny:
        url=pokemon_dict[pokemon]["sprite"]["shiny"]
    else:
        url=pokemon_dict[pokemon]["sprite"]["regular"]

    urlresponse = requests.get(url, timeout=5)
    return Image.open(BytesIO(urlresponse.content))

def triggers_handler(trigger: str, pokemonname: str, shinyradio: str):
    """
    Function to handle the triggers of the app.
    """
    global chaintext

    if trigger == "add1_btn":
        # + button was clicked
        # Add 1 to the number of times caught and update the pokemon_db
        pokemon_dict[pokemonname]["times_caught"] += 1
        # Add 1 to the chain if the pokemon is the same as the last one caught
        # or reset the chain if a different pokemon was caught
        if pokemonchain_dict["pokemonname"] != pokemonname:
            pokemonchain_dict["pokemonname"] = pokemonname
            pokemonchain_dict["chainvalue"] = 0

        # Update chain text and chain value
        pokemonchain_dict["chainvalue"] += 1
        pokemonchain_dict["chaintext"] = f'Chain of {pokemonchain_dict["chainvalue"]} {pokemonname.split("-")[-1]}!'
        chaintext = html.Td(pokemonchain_dict["chaintext"], style={"color":"SteelBlue" ,"font-weight": "bold"})
    elif ctx.triggered_id == "resetchain_btn":
        # Reset button was clicked
        pokemonchain_dict["chainvalue"] = 0
        pokemonchain_dict["chaintext"] = "No chain"
        chaintext = html.Td(pokemonchain_dict["chaintext"], style={"font-weight": "normal"})
    elif ctx.triggered_id == "shinyradio":
        # Shiny radio button was clicked
        # Set the shiny_caught value in the pokemon_db
        pokemon_dict[pokemonname]["shiny_caught"] = shinyradio

    # Update the pokemon_db and utils.json files
    with open(DATABASE_PATH, "w", encoding="utf-8") as database,\
         open(UTILS_PATH, "w", encoding="utf-8") as utils:
        json.dump(pokemon_db, database, indent=4)
        json.dump(utils_json, utils, indent=4)

#%% Dash app
pokemontocatch = choice(list(pokemon_dict.keys()))
combatpower = randint(1, 1000)

app = Dash()
server = app.server
app.title = "PokemonCatcher"

app.layout = (
    html.Div(
        [
            html.Img(src=game_logo, style={"width": "15%"}),
            html.H1("Catch Rate Calculator"),
            # Input data
            html.H3("Input data:"),
            html.Table(
                [
                    html.Tr(
                        [
                            html.Td("Pokemon to catch:"),
                            html.Td(
                                dcc.Dropdown(
                                    list(pokemon_dict.keys()),
                                    id="pokemonname",
                                    value=pokemontocatch,
                                )
                            ),

                        ]
                    ),
                    html.Tr(
                        [
                            html.Td("Pokemon cry:"),
                            html.Td(html.Audio(
                                id="cryaudio",
                                controls=True,
                                autoPlay=False,
                                hidden=False,

                            )),
                        ]
                    ),
                    html.Tr(
                        [
                            html.Td("Shiny caught:"),
                            dcc.RadioItems(['Yes', 'No'], id="shinyradio", value='No', inline=True),
                        ]
                    ),
                    html.Tr(
                        [
                            html.Td("Number caught:"),
                            html.Td(id="numbercaught", style={'border': '1px solid LightGray'}),
                            html.Button("+", id="add1_btn"),
                        ]
                    ),
                    html.Tr(
                        [
                            html.Td("Catch chain:"),
                            html.Td(id="chaintext", style={'border': '1px solid LightGray'}),
                            html.Button("Reset", id="resetchain_btn"),
                        ]
                    ),
                    html.Tr(
                        [
                            html.Td("CP:"),
                            html.Td(
                                dcc.Input(id="cp", type="number", value=combatpower, style={'border': '1px solid LightGray', 'textAlign': 'center'})
                            ),
                        ]
                    ),
                    html.Tr(
                        [
                            html.Td("Pokeball type:"),
                            html.Td(
                                dcc.Dropdown(
                                    list(ballrate_dict.keys()),
                                    id="ball",
                                    value="pokeball",
                                )
                            ),
                        ]
                    ),
                    html.Tr(
                        [
                            html.Td("Berry type:"),
                            html.Td(
                                dcc.Dropdown(
                                    list(berry_dict.keys()), id="berry", value="none"
                                )
                            ),
                        ]
                    )
                ],
            style={"margin-left":"auto", "margin-right":"auto"}),
            html.Br(),
            # Output data
            html.H3("Catch rates for each technique:"),
            html.Table(
                [
                    html.Tr(id = "CRNone"),
                    html.Tr(id = "CRNice"),
                    html.Tr(id = "CRGreat"),
                    html.Tr(id = "CRExcellent"),
                ],
            style={"margin-left":"auto", "margin-right":"auto"},
            ),
            html.Img(id="sprite_shiny"),
            html.Img(id="sprite_regular"),
        ]
    , style={'textAlign': 'center'}),
)

#%% Callbacks
@callback(
    output=[Output("CRNone", "children"),
            Output("CRNice", "children"),
            Output("CRGreat", "children"),
            Output("CRExcellent", "children"),
            Output("numbercaught", "children"),
            Output("chaintext", "children"),
            Output("sprite_shiny", "src"),
            Output("sprite_regular", "src"),
            Output("shinyradio", "value"),
            Output("cryaudio", "src")
            ],
    inputs=[Input("pokemonname", "value"),
            Input("cp", "value"),
            Input("ball", "value"),
            Input("berry", "value"),
            Input("shinyradio", "value"),
            Input("add1_btn", "n_clicks"),
            Input("resetchain_btn", "n_clicks")
            ],
    running=[
            (Output("add1_btn", "disabled"), True, False),
            (Output("resetchain_btn", "disabled"), True, False)
            ]
)
def update_catchrates(pokemonname, cp, ball, berry, shinyradio, *_):
    """
    Callback function to update the catch rates based on the input data.
    """
    global INIT_STATE
    if INIT_STATE:
        # Set the initial state of the app
        global chaintext
        chaintext = html.Td(pokemonchain_dict["chaintext"],
                            style={"color":"SteelBlue" ,"font-weight": "bold"})
        INIT_STATE = False

    # Triggers
    triggers_handler(ctx.triggered_id, pokemonname, shinyradio)

    shinyradio = pokemon_dict[pokemonname]["shiny_caught"]

    # Get the pokemon cry
    cryaudio = pokemon_dict[pokemonname]["cry"]
    # Get the sprites for the pokemon
    sprite_regular = get_sprite(pokemonname, shiny=False)
    sprite_shiny = get_sprite(pokemonname, shiny=True)

    # Get the catch rates for the pokemon
    techniquerate_df = catch_pokemon(
        pokemon=pokemonname, combat_power=cp, ball=ball, berry=berry
    )

    # Set the catch ring color based on the catch rate
    ringcolor_dict = {
        "None": catchring_color(techniquerate_df["Catch Rate"][0]),
        "Nice": catchring_color(techniquerate_df["Catch Rate"][1]),
        "Great": catchring_color(techniquerate_df["Catch Rate"][2]),
        "Excellent": catchring_color(techniquerate_df["Catch Rate"][3]),
    }

    return (
        html.Td(f'None         {techniquerate_df["Catch Rate"][0]}%', style={"border": f'4px solid {ringcolor_dict["None"]}', "font-weight": "bold"}),
        html.Td(f'Nice         {techniquerate_df["Catch Rate"][1]}%', style={"border": f'4px solid {ringcolor_dict["Nice"]}', "font-weight": "bold"}),
        html.Td(f'Great        {techniquerate_df["Catch Rate"][2]}%', style={"border": f'4px solid {ringcolor_dict["Great"]}', "font-weight": "bold"}),
        html.Td(f'Excellent    {techniquerate_df["Catch Rate"][3]}%', style={"border": f'4px solid {ringcolor_dict["Excellent"]}', "font-weight": "bold"}),
        pokemon_dict[pokemonname]["times_caught"],
        chaintext,
        sprite_regular,
        sprite_shiny,
        shinyradio,
        cryaudio
    )
#%% Run the app
if __name__ == "__main__":
    app.run(debug=True, port=8050)
