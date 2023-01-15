from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS, cross_origin

from neo4j import GraphDatabase
import re

import time
import os
app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

# Connect to the Neo4J server
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))


def make_node_id_from_name(name):
    node_id = str(name).strip()
    #lowercase
    node_id = node_id.lower()
    #replace non-alphanumeric characters with underscore
    node_id = re.sub(r'\W+', '_', node_id)
    return node_id

@app.route("/persons", methods=["POST"])
def create_node():
    data = request.get_json()
    name = data["name"] 
    additional_data = data["additional_data"]
    additional_data["created_at"] = time.time()
    node_id = make_node_id_from_name(name)
    
    with driver.session() as session:
        #check if node already exists
        result = session.run(
            "MATCH (a:Person) WHERE a.node_id = $node_id RETURN a",
            node_id=node_id
        )
        node = result.single()
        if node:
            return jsonify({"message": "Node already exists", "node_id": node_id}), 400

        query = "CREATE (a:Person {node_id: $node_id, name: $name, "
        for key, value in additional_data.items():
            query += key + ": $" + key + ", "
        query = query[:-2] + "}) RETURN a"
        result = session.run(query, node_id=node_id, name=name, **additional_data)
        node = result.single()[0]
        data = {}
        node = dict(node)
        print(node)
        for key, value in node.items():
            data[key] = value
        return jsonify({"message": "Node created", "node_id": node_id, "data": node}), 201

@app.route("/persons", methods=["GET"])
def read_node():
    with driver.session() as session:
        result = session.run(
            "MATCH (a:Person) RETURN a"
        )
        nodes = result.values()
        data = []
        for node in nodes:
            node_data = {}
            node = dict(node[0])
            for key, value in node.items():
                node_data[key] = value
            data.append(node_data)
        return jsonify({"message": "Nodes read", "data": data}), 200

@app.route("/persons/<node_id>", methods=["GET"])
def read_node_by_node_id(node_id):
    with driver.session() as session:
        result = session.run(
            "MATCH (a:Person) WHERE a.node_id = $node_id RETURN a",
            node_id=node_id
        )
        result = result.single()
        if result is None:
            return jsonify({"message": "Node not found"}), 404

        node = result[0]
        data = {}
        for key, value in node.items():
            data[key] = value
        return jsonify({"message": "Node read", "data": data}), 200


@app.route("/persons/<node_id>", methods=["PUT"])
def update_node(node_id):
    data = request.get_json()
    name = data["name"]
    additional_data = data["additional_data"]

    with driver.session() as session:
        #check if node exists
        result = session.run(
            "MATCH (a:Person) WHERE a.node_id = $node_id RETURN a",
            node_id=node_id
        )
        result = result.single()
        if result is None:
            return jsonify({"message": "Node not found"}), 404
        query = "MATCH (a:Person {node_id: $node_id}) SET a.name = $name, "
        for key, value in additional_data.items():
            query += "a." + key + " = $" + key + ", "
        query = query[:-2] + " RETURN a"
        result = session.run(
            query,
            node_id=node_id, name=name, **additional_data
        )
        node = result.single()[0]
        data = {}
        for key, value in node.items():
            data[key] = value
        return jsonify({"message": "Node updated", "data": data}), 200

@app.route("/persons/<node_id>", methods=["DELETE"])
def delete_node(node_id):
    #find and delete all relationships associated with the node
    #then delete the node
    with driver.session() as session:
        session.run("MATCH (a:Person)-[r]-() WHERE a.node_id = $node_id DELETE r", node_id=node_id)

    return jsonify({"message": "Node deleted", "node_id": node_id})
        

@app.route("/relationships", methods=["POST"])
def create_relationship():
    data = request.get_json()
    start_node_id = data["start_node_id"]
    end_node_id = data["end_node_id"]
    relationship_type = data["relationship_type"]
    #replace spaces with underscore
    rType = relationship_type.replace(" ", "_")
    relationship_id = start_node_id  + "_" + end_node_id
    with driver.session() as session:
        #check if relationship already exists
        exists = session.run(
            "MATCH (a:Person)-[r]->(b:Person) WHERE a.node_id = $start_node_id AND b.node_id = $end_node_id RETURN r",
            start_node_id=start_node_id, end_node_id=end_node_id
        )
        if exists.single():
            return jsonify({"message": "Relationship already exists"}), 400
        result = session.run(
            "MATCH (a:Person), (b:Person) WHERE a.node_id = $start_node_id AND b.node_id = $end_node_id CREATE (a)-[r:"+rType+" {relationship_id: $relationship_id, type: $relationship_type}]->(b) RETURN r, b",
            start_node_id=start_node_id, end_node_id=end_node_id, relationship_id=relationship_id, relationship_type=relationship_type
        )
        relationship = result.single()[0]
        return jsonify({"relationship_id": relationship["relationship_id"], "type": relationship["type"], "end_node_id": end_node_id, "end_node_name": end_node_id})



@app.route("/relationships/<node_id>", methods=["GET"])
def read_relationships(node_id):
    with driver.session() as session:
        try:
            result = session.run(
                "MATCH (a:Person)-[r]->(b:Person) WHERE a.node_id = $node_id RETURN a, r, b",
                node_id=node_id
            )
        except Exception as e:
            return jsonify({"message": "Node not found", "relationships": []}), 200
        
        relationships = []
        for record in result:
            start_node = record[0]
            relationship = record[1]
            end_node = record[2]
            relationships.append({
                "start_node_id": start_node["node_id"],
                "start_node_name": start_node["name"],
                "relationship_id": relationship["relationship_id"],
                "type": relationship["type"],
                "end_node_id": end_node["node_id"],
                "end_node_name": end_node["name"]
            })
        return jsonify({"relationships": relationships})


@app.route("/relationships", methods=["GET"])
def read_all_relationships():
    with driver.session() as session:
        result = session.run(
            "MATCH (a:Person)-[r]->(b:Person) RETURN a, r, b"
        )
        relationships = []
        for record in result:
            start_node = record[0]
            relationship = record[1]
            end_node = record[2]
            relationships.append({
                "start_node_id": start_node["node_id"],
                "start_node_name": start_node["name"],
                "relationship_id": relationship["relationship_id"],
                "type": relationship["type"],
                "end_node_id": end_node["node_id"],
                "end_node_name": end_node["name"]
            })
        return jsonify({"relationships": relationships})

#DONT USE THIS
@app.route("/relationship/<int:relationship_id>", methods=["PUT"])
def update_relationship(relationship_id):
    data = request.get_json()
    new_type = data["relationship_type"]
    rType = new_type.replace(" ", "_")
    with driver.session() as session:
        #get the start and end node ids
        result = session.run(
            "MATCH (a:Person)-[r]->(b:Person) WHERE r.relationship_id = $relationship_id RETURN a.node_id, b.node_id",
            relationship_id=relationship_id
        )
        start_node_id = result.single()[0]
        end_node_id = result.single()[1]
        #delete the relationship
        session.run(
            "MATCH (a:Person)-[r]->(b:Person) WHERE r.relationship_id = $relationship_id DELETE r",
            relationship_id=relationship_id
        )
        #create the new relationship
        result = session.run(
            "MATCH (a:Person), (b:Person) WHERE a.node_id = $start_node_id AND b.node_id = $end_node_id CREATE (a)-[r:"+rType+" {relationship_id: $relationship_id, type: $relationship_type}]->(b) RETURN r, b",
            start_node_id=start_node_id, end_node_id=end_node_id, relationship_id=relationship_id, relationship_type=new_type
        )
        
        return jsonify({"message": "Relationship updated", "relationship_id": relationship_id, "type": new_type, "end_node_id": end_node_id, "start_node_id": start_node_id, "end_node_name": result.single()[1]["name"]})

@app.route("/relationships/<relationship_id>", methods=["DELETE"])
def delete_relationship(relationship_id):
    with driver.session() as session:
        result = session.run(
            "MATCH ()-[r]-() WHERE r.relationship_id = $relationship_id DELETE r RETURN r",
            relationship_id=relationship_id
        )
        return jsonify({"message": "Relationship deleted", "relationship_id": relationship_id})


@app.route("/export/<type>", methods=["GET"])
def export(type):
    #available types: csv, csv-matrix, json
    #everything included
    if type == "csv":
        with driver.session() as session:
            result = session.run(
                "MATCH (a:Person)-[r]->(b:Person) RETURN a.node_id, a.name, r.type, b.node_id, b.name"
            )
            csv = "source,source_name,type,target,target_name"
            for record in result:
                csv += f"\n{record[0]},{record[1]},{record[2]},{record[3]},{record[4]}"
            return Response(
                csv,
                mimetype="text/csv",
                headers={"Content-disposition":
                         "attachment; filename=export.csv"})
    elif type == "csv-matrix":
        with driver.session() as session:
            result = session.run(
                "MATCH (a:Person)-[r]->(b:Person) RETURN a.node_id, a.name, r.type, b.node_id, b.name"
            )
            # None, Target Name 1, Target Name 2, Target Name 3
            # Target Name 1, X, type, type
            # Target Name 2, type, type, type

            #make matrix
            matrix = {}
            for record in result:
                if record[1] not in matrix:
                    matrix[record[1]] = {}
                matrix[record[1]][record[4]] = record[2]
            #make csv
            csv = "A/B"
            for key in matrix:
                csv += "," + key
            for key in matrix:
                csv += f"\n{key}"
                for key2 in matrix:
                    #check if same
                    if key == key2:
                        csv += ",X"
                    elif key2 in matrix[key]:
                        csv += "," + matrix[key][key2]
                    else:
                        csv += ","
            return Response(
                csv,
                mimetype="text/csv",
                headers={"Content-disposition":
                         "attachment; filename=export.csv"})
    elif type == "json":
        with driver.session() as session:
            result = session.run(
                "MATCH (a:Person)-[r]->(b:Person) RETURN a.node_id, a.name, r.type, b.node_id, b.name"
            )
            relationships = []
            for record in result:
                relationships.append({
                    "source": record[0],
                    "source_name": record[1],
                    "type": record[2],
                    "target": record[3],
                    "target_name": record[4]
                })
            return jsonify({"links": relationships})
    else:
        return jsonify({"message": "Invalid export type"}), 400


@app.route("/import/<type>", methods=["POST"])
def import_data(type):
    if type == "csv-matrix":
        matrix = {}
        #build matrix
        data = request.data.decode("utf-8")
        lines = data.split("\n")
        for line in lines:
            line = line.split(",")
            if line[0] == "A/B":
                #header
                for i in range(1, len(line)):
                    matrix[line[i]] = {}
            else:
                #data
                for i in range(1, len(line)):
                    matrix[line[0]][list(matrix.keys())[i-1]] = line[i]
        
        with driver.session() as session:
            #create or replace nodes
            for key in matrix:
                node_id = make_node_id_from_name(key)
                session.run(
                    "MERGE (a:Person {node_id: $node_id, name: $name})",
                    node_id=node_id, name=key
                )

            #create or replace relationships
            for key in matrix:
                for key2 in matrix[key]:
                    if matrix[key][key2] != "X":
                        start_node_id = make_node_id_from_name(key)
                        end_node_id = make_node_id_from_name(key2)
                        relationship_id = make_relationship_id(start_node_id, end_node_id)
                        session.run(
                            "MATCH (a:Person), (b:Person) WHERE a.node_id = $start_node_id AND b.node_id = $end_node_id MERGE (a)-[r:RELATIONSHIP {relationship_id: $relationship_id, type: $relationship_type}]->(b)",
                            start_node_id=start_node_id, end_node_id=end_node_id, relationship_id=relationship_id, relationship_type=matrix[key][key2]
                        )
            return jsonify({"message": "Imported"})
    else:
        return jsonify({"message": "Invalid import type"}), 400



if __name__ == '__main__':
      app.run(host='0.0.0.0', port=8000)
