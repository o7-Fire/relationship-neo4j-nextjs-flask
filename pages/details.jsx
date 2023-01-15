import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import MenuItem from '@mui/material/MenuItem';
import InputLabel from '@mui/material/InputLabel';
import FormControl from '@mui/material/FormControl';
import Select from '@mui/material/Select';
import Link from 'next/link'

import {Inter} from '@next/font/google'
import {useEffect, useState} from 'react'
import {useRouter} from 'next/router'

const inter = Inter({ subsets: ['latin'] })

export async function getStaticProps(context) {
    return {
        props: {
            API_URL: process.env.API_HOST ? process.env.API_HOST : '/api/'
        }
    }
}

export default function Create({API_URL}) {
    const router = useRouter();

    console.log(router.query);


    const [query, setQuery] = useState(router.query)
    const [persons, setPersons] = useState(null)
    const [relationships, setRelationships] = useState(null)
    const [isLoading, setLoading] = useState(false)
    const [relationshipTarget, setRelationshipTarget] = useState('')

    const queryId = router.query.node_id;

    const edit = !!queryId;

    useEffect(() => {
        console.log("useEffect called");
        console.log(queryId);

        if (edit) {
            setLoading(true)
            fetch(API_URL + `relationships/${queryId}`)
                .then((res) => res.json())
                .then((data) => {
                    console.log(data)
                    setRelationships(data.relationships)
                    setLoading(false)
                });

            fetch(API_URL + `persons`)
                .then((res) => res.json())
                .then((data) => {

                    //remove the current person from the list then assign it to query
                    let currentPerson = data.persons.filter((person) => person.node_id == queryId)[0]
                    console.log(currentPerson)
                    //remove
                    const persons = data.persons = data.persons.filter((person) => person.node_id != queryId)
                    console.log(persons)
                    setPersons(persons)
                    setQuery(currentPerson)



                });


        } else {
            //default
            setQuery({
                name: 'Nexity',
                age: 0
            })
        }
    }, [router.isReady])


    if (isLoading) return <p>Loading...</p>

    function send() {
        console.log("Send")
        const name = query.name
        const age = query.age

        fetch(API_URL + `persons` + (edit ? `/${queryId}` : ''), {
            method: edit ? 'PUT' : 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                age: age
            })
        })
            .then((res) => res.json())
            .then((data) => {
                console.log(data)
                //update state
                if(edit)setQuery(data)
                else router.push('/');
                
            })
    }


    const peoplesFiltered = [];
    const alreadyAdded = [];
    if (relationships)
        relationships.forEach((relationship) => {
            alreadyAdded.push(relationship.end_node_id)
        });
    console.log(alreadyAdded)
    if (persons)
        persons.forEach((person) => {
            if (!alreadyAdded.includes(person.node_id)) {
                peoplesFiltered.push(person)
            }
        });


    return (
        <main>
            <div>
                <Link href={'/'} passHref><Button>Home</Button></Link>
                <h1>
                    {edit ? 'Edit' : 'Create'} Person
                </h1>
            </div>

            <Box
                component="form"
                sx={{
                    '& > :not(style)': { m: 1, width: '25ch' },
                    display: 'flex',
                    flexDirectionq: 'collumn'
                }}
                noValidate
                autoComplete="off"
            >
                <TextField id="name" label="Name" type="text" defaultValue="Nexity" variant="outlined" {...({
                    value: query.name, onChange: (e) => {
                        setQuery({ ...query, name: e.target.value })
                    }
                })} required />
                <TextField id="age" label="Age" variant="outlined" defaultValue="18" type="number" {...({
                    value: query.age, onChange: (e) => {
                        setQuery({ ...query, age: e.target.value })
                    }
                })} required />

                <Button onClick={send} variant="contained">{edit ? 'Edit' : 'Create'}</Button>
            </Box>

            <Stack spacing={2}>
                {relationships && relationships.map((relationship) => (
                    <Paper elevation={3} sx={{ p: 2, width: '100%' }} key={relationship.end_node_id}>
                        <a href={`/details?node_id=${relationship.end_node_id}`}><h2>{relationship.end_node_name}</h2></a>
                        <p>{relationship.type}</p>
                        <Button onClick={() => {
                            if (relationship.relationship_id !== undefined){
                                fetch(API_URL + `relationships/${relationship.relationship_id}`, {
                                    method: 'DELETE',
                                    headers: {
                                        'Content-Type': 'application/json'
                                    }
                                })
                                    .then((res) => res.json())
                                    .then((data) => {
                                        console.log(data)
                                        //update local state
                                        const newRelationships = relationships.filter((r) => r.relationship_id !== relationship.relationship_id)
                                        console.log(newRelationships)
                                        setRelationships(newRelationships)

                                    })
                            }

                        }} variant="contained">Delete</Button>
                    </Paper>
                ))}

                <Box style={{ display: peoplesFiltered.length > 0 ? 'block' : 'none' }}>
                    <FormControl variant="standard" sx={{ m: 1, minWidth: 120 }}>
                        <InputLabel id="relationship-target-label">Relationship Target</InputLabel>
                        <Select
                            labelId="relationship-target-label"
                            id="relationship-target"
                            label="Relationship Target"
                            value={relationshipTarget}
                            onChange={(e) => {
                                setRelationshipTarget(e.target.value)
                            }}

                        >
                            <MenuItem value="">
                                <em>None</em>
                            </MenuItem>
                            {peoplesFiltered && peoplesFiltered.map((person) => {
                                return (
                                    <MenuItem value={person.node_id} key={person.node_id}>{person.name}</MenuItem>
                                )
                            })}
                        </Select>
                    </FormControl>
                    <TextField id="relationship_description" label="Description" type="text" variant="outlined" required />
                    <Button variant="contained" onClick={() => {
                        console.log("Add Relationship")
                        let start_node_id = queryId;
                        let end_node_id = relationshipTarget;
                        let relationship_type = document.getElementById("relationship_description").value;
                        //check for empty
                        if (!start_node_id || !end_node_id || !relationship_type) {
                            return;
                        }
                        fetch(API_URL + `relationships`, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                start_node_id: start_node_id,
                                end_node_id: end_node_id,
                                relationship_type: relationship_type
                            })
                        })
                            .then((res) => res.json())
                            .then((data) => {
                                console.log(data)
                                //update local state
                                setRelationships([...relationships, data])
                            })
                    }}>Add Relationship</Button>
                </Box>

            </Stack>



        </main>
    )
}