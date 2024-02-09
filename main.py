"""Script to retrieve the history about shielded pool value on the Horizen blockchain.

The script expects a local Zend instance running and exposing the RPC interface on port 8231.
Extracted data are stored in a CSV file to speed up the execution.
The CSV file is updated (append) every time the script runs and finds new blocks.
"""

import argparse
import csv

import requests
from requests.auth import HTTPBasicAuth

import matplotlib.pyplot as plt

import plotly.express as px

CSV_FILE_PATH = 'mainnet_shielded_pool.csv'

RPC_ENDPOINT_URL = 'http://127.0.0.1:8231/'
RPC_TIMEOUT = 10 # seconds

# Replace following variables with proper username and password set at zend startup.
RPC_USERNAME = "dummy_user"
RPC_PASSWORD = "dummy_password"

def get_block_sprout_chain_value(block_height: int) -> float:
    """Gets the amount of Zen in the shielded pool at a specific block height.

    Args:
        block_height (int): The height of the block to be queried.

    Returns:
        float: The amount of Zen in the (sprout) shielded pool.
    """
    payload_data = {"jsonrpc": "1.0", "id": "curltest", "method": "getblock", "params": [str(block_height)] }
    response = requests.post(RPC_ENDPOINT_URL, json=payload_data, auth=HTTPBasicAuth(RPC_USERNAME, RPC_PASSWORD), headers={'content-type': 'application/json'}, timeout=RPC_TIMEOUT)

    if response.status_code == 200:
        response_data = response.json()
        return response_data["result"]["valuePools"][0]["chainValue"]


    print(f"An error occurred while requesting data: {response.status_code} - {response.text}")
    exit()

def get_csv_data(filepath: str) -> tuple[list[int], list[float]]:
    """Loads data from a CSV file containing pairs ([block_height], [shielded_pool_value]).

    Args:
        filepath (str): The path of the CSV file to read.

    Returns:
        tuple[list[int], list[float]]: The two lists of data (the first one contains all the known block heights, the second one the related values for the shielded pool).
    """

    block_height_data = []
    shielded_pool_data = []

    with open(filepath, 'r', encoding='utf8') as csv_file:
        reader = csv.reader(csv_file)

        # Skip the first line (CSV header)
        next(reader)

        for row in reader:
            block_height_data.append(int(row[0]))
            shielded_pool_data.append(float(row[1]))

    return (block_height_data, shielded_pool_data)

def get_last_block_from_csv(filepath: str) -> int:
    """Gets the last block height from the CSV file.

    Args:
        filepath (str): The path of the CSV file.

    Returns:
        int: The height of the last block available on the CSV file.
    """

    data = get_csv_data(filepath)

    return data[0][-1]

def get_last_block_from_zend() -> int:
    """Gets the last block height of the current blockchain tip from Zend.

    Returns:
        int: The height of the current tip.
    """

    payload_data = {"jsonrpc": "1.0", "id": "curltest", "method": "getblockcount"}
    response = requests.post(RPC_ENDPOINT_URL, json=payload_data, auth=HTTPBasicAuth(RPC_USERNAME, RPC_PASSWORD), headers={'content-type': 'application/json'}, timeout=RPC_TIMEOUT)

    if response.status_code == 200:
        response_data = response.json()
        return int(response_data["result"])

def update_csv_file(filepath: str, start_height: int, end_height: int):
    """Updates the CSV file with data collected for blocks in range [start_height, end_height] (both inclusive).

    Args:
        filepath (str): The path of the CSV file.
        start_height (int): The height of the first block to be appended to the CSV file.
        end_height (int): The height of the last block to be appended to the CSV file.
    """

    abort_requested = False
    data = []

    try:
        for i in range(start_height, end_height + 1):
            data.append([i, get_block_sprout_chain_value(i)])

            # Write a progress update every 10k processed blocks
            if i % 10000 == 0:
                print(f"Processing block {i}/{end_height} [{(i * 100 // end_height)}%]")
    except KeyboardInterrupt:
        print("\nSaving data and quitting...")
        abort_requested = True

    with open(filepath, 'a', newline='', encoding="utf8") as csv_file:
        csv_writer = csv.writer(csv_file)

        # Write the data to the CSV file
        csv_writer.writerows(data)

    if abort_requested:
        quit(0)

def verify_csv_file(filepath: str):
    """Verifies whether the CSV file is consistent or not.

    In particular, it checks whether all block heights are consecutive.

    Args:
        filepath (str): The path of the CSV file to be verified.
    """

    (blocks, _) = get_csv_data(filepath)

    for index in range(1, len(blocks)):
        if blocks[index] != blocks[index - 1] + 1:
            print(f"Unexpected entry {blocks[index]}, previous value {blocks[index - 1]}")

def show_chart(csv_file_path: str, start_height: int):
    """Display a chart showing the value of the shielded pool starting from a specific height.

    This function uses Matplotlib.

    Args:
        csv_file_path (str): The path of the CSV file to use as input data.
        start_height (int): The height of the first block to show on the chart (use 0 to show all data).
    """

    csv_data = get_csv_data(csv_file_path)

    _, ax = plt.subplots()
    ax.plot(csv_data[0][start_height:], csv_data[1][start_height:], label='Line Chart')

    ax.format_coord = lambda x,y: f"x={x}, y={y}"

    plt.show()

def show_chart_experimental(csv_file_path: str, start_height: int):
    """Display a chart showing the value of the shielded pool starting from a specific height.

    This function uses plotly.py.

    Args:
        csv_file_path (str): The path of the CSV file to use as input data.
        start_height (int): The height of the first block to show on the chart (use 0 to show all data).
    """

    csv_data = get_csv_data(csv_file_path)

    fig = px.line(x=csv_data[0][start_height:],
                  y=csv_data[1][start_height:],
                  title="Horizen shiedeld pool value")
    fig.show()

def parse_arguments():
    """Defines and parses command line arguments.

    Returns:
        _type_: _description_
    """
    parser = argparse.ArgumentParser(description='A tool that retrieves shielded pool value from Zend and plots it.')
    parser.add_argument('--plot_from_height', help='Starting height for the plot (x axis)')
    parser.add_argument('--no_update', action='store_true', help='Skip the connection to a node to retrieve new blocks data and update the CSV')
    parser.add_argument('--verify_data', action='store_true', help='Request to validate data stored in the CSV file')
    parser.add_argument('--experimental', action='store_true', help='Show the experimental chart based on plotly.py')
    return parser.parse_args()

def main():
    """Entry point of the script"""

    args = parse_arguments()
    start_height = 0

    if args.verify_data:
        verify_csv_file(CSV_FILE_PATH)
        return

    if args.plot_from_height is not None:
        start_height = int(args.plot_from_height)

    if not args.no_update:
        try:
            last_checked_block = get_last_block_from_csv(CSV_FILE_PATH)
        except FileNotFoundError:
            with open('mainnet_shielded_pool.csv', 'w', encoding='utf8') as csv_file:
                csv_file.write("BLOCK HEIGHT,SHIELDED POOL VALUE\n")

            last_checked_block = -1
        except IndexError:
            last_checked_block = -1

        last_available_block = get_last_block_from_zend()

        print(f"Last CSV block: {last_checked_block}")
        print(f"Last Zend block: {last_available_block}")

        if last_checked_block < last_available_block:
            update_csv_file(CSV_FILE_PATH, last_checked_block + 1, last_available_block)

    if args.experimental:
        show_chart_experimental(CSV_FILE_PATH, start_height)
    else:
        show_chart(CSV_FILE_PATH, start_height)



main()
