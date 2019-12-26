import React from 'react';
import SimpleMap from "./components/react-map";
import './App.css';


function App() {
  return (
    <div className="container">
      <h2> Rijkswaterstaat Measurements </h2>
        <SimpleMap />
    </div>
  );
}

export default App;

