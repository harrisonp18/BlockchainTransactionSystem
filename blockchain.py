#Author: Harrison Paxton
#Project: Blockchain Transaction System
#With help from Daniel van Flymen

import hashlib
import json
from time import time
from textwrap import dedent
from uuid import uuid4
import requests
from flask import Flask, jsonify, request, render_template
from urllib.parse import urlparse


class Blockchain(object):
    def __init__(self):
        self.chain = [] #list of blocks
        self.transaction_list = [] #list of transactions
        self.nodes = set() #holds list of nodes

        ## genesis block
        self.create_block(previous_hash = 1, proof = 100)

    def register_node(self, address):
        #adds new node

        parsed_url =urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def validate_chain(self, chain):
        #validates the blockchain by making sure its the most recent (longest)

        previous_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{previous_block}')
            print(f'{block}')
            print("\n----------\n")

            if block['previous_hash'] != self.block_hash(previous_block): ## check to see if hash is right
                return False

            if not self.validate_proof(previous_block['proof'], block['proof']): ##checks that pow is correct
                return False

            previous_block = block
            current_index =+ 1

        return True


    def consensus(self):
        #consensus algorithm, replaces chain with updated one

        neighbors = self.nodes
        updated_chain = None

        maximum_chain = len(self.chain)

        for node in neighbors:
            response = requests.get(f'http://{node}/chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if length > maximum_chain and self.validate_chain(chain): ##compares chains
                        maximum_chain = length
                        updated_chain = chain
            
            if updated_chain: ##replace chain if newer one is found
                self.chain = updated_chain
                return True
            
            return False



    def create_block(self, proof, previous_hash):
    #adds block to chain
        block = {
            'index': len(self.chain) + 1,    ##location in chain
            'time': time(),     ##time block was created
            'transactions': self.transaction_list,
            'proof': proof,   ##calculated by proof of work algorithm
            'previous_hash': previous_hash,
        }

        ##update transaction list
        self.transaction_list = []

        ##add new block to chain
        self.chain.append(block)
        return block

    

    def create_transaction(self, sender, receiver, value, note):    
        #adds transaction to transaction_list

        self.transaction_list.append({ 
            'sender': sender,   ##sender (address string)
            'receiver': receiver,   ##receiver address (string)
            'value': value,     ##amount including in transaction (int)
            'note': note,   ##notes to be added to transaction (string)
        })

        return self.final_block['index'] + 1 ##returns to next block to be mined 
    
    @property
    def final_block(self):     
        #returns the final block at the time
        return self.chain[-1]


    @staticmethod 
    def block_hash(block):    
        ##hashes the blocks, this is what makes chain immutable, each block holds hash of previous block
        ## SHA-256 hash used

        hash_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(hash_string).hexdigest()

    def proof_of_work(self, previous_proof):
        ##pow algorithm
        ## finds new proof based of previous one

        proof = 0
        while self.validate_proof(previous_proof, proof) is False:
            proof+=1

        return proof

    @staticmethod
    def validate_proof(previous_proof, proof):
        ##validate proof

        validate = f'{previous_proof}{proof}'.encode()
        validate_hash = hashlib.sha256(validate).hexdigest()
        return validate_hash[:4] == "0000"

    
##code below here is to create "server", API endpoints

app = Flask(__name__)

node_identifier = str(uuid4()).replace('-','')

blockchain = Blockchain()

@app.route('/')
def home():
    return render_template("home.html")

@app.route('/input')
def input():
    return render_template("input.html")

##transaction function
@app.route('/transactions/new', methods= ['POST'])
def new_transaction():
    values = request.get_json()

    ##verify the fields all have entries
    required = ['sender', 'receiver', 'value', 'note']
    if not all(k in values for k in required):
        return 'Missing values', 400

    ##creates transaction
    index = blockchain.create_transaction(values['sender'], values['receiver'], values['value'], values['note'])

    response = {'message': f'Transaction added to block {index}'}
    return jsonify(response), 201

##mine function
@app.route('/mine', methods=["GET"])
def mine():
    ## run pow algorithm
    previous_block = blockchain.final_block
    previous_proof = previous_block['proof']
    proof = blockchain.proof_of_work(previous_proof)

    ##when block is mined, "miner" receives a coin
    blockchain.create_transaction(
        sender='0',
        receiver=node_identifier,
        value=1,
        note='You have been rewarded 1 coin'
    )

    ##add the mined block to chain
    previous_hash = blockchain.block_hash(previous_block)
    block = blockchain.create_block(proof, previous_hash)

    response = {
        'message': "New Block Mined",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return jsonify(response), 200

##return chain function
@app.route('/chain', methods=['GET'])
def full_chain():
    response ={
        'blockchain': blockchain.chain,
        'blockchain_length': len(blockchain.chain),
    }
    return jsonify(response), 200

##registers new nodes
@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "No nodes added", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'Nodes added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

## runs consensus algorithm
@app.route('/nodes/resolve', methods=['GET'])
def resolve():
    replaced = blockchain.consensus()

    if replaced:
        response = {
            'message': 'The chain was updated',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'The chain is the up to date',
            'chain': blockchain.chain
        }

    return jsonify(response), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    

