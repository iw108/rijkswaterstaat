import React from "react";

const mapSelect = [
    'waterhoogte-t-o-v-nap',
    'astronomische-getij',
    'waterafvoer',
    'wind',
    'watertemperatuur',
    'stroming',
    'golfhoogte'
];


const TestSelect = ({onChange}) => {
    return (
        <select name="maps" id="map-select" onChange={onChange}>
            <option hidden >Select map type</option>
                {mapSelect.map(item => <option key={item} value={item}>{item}</option>)}
        </select>
    )
};

export default TestSelect;
