
import React, { Component } from 'react';
import MapGL, { Marker, Popup } from 'react-map-gl';
import TestSelect  from "./map-select";
import proj4 from "proj4";
import Pin from "./pin";
import MarkerInfo from "./marker-info";
import 'mapbox-gl/dist/svg/mapboxgl-ctrl-zoom-in.svg';
import 'mapbox-gl/dist/svg/mapboxgl-ctrl-zoom-out.svg';

proj4.defs("EPSG:25831", "+proj=utm +zone=31 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs");


// const navStyle = {
//   position: 'absolute',
//   top: 0,
//   left: 0,
//   padding: '10px'
// };


class SimpleMap extends Component {

  state = {
    viewState: {
      width: 600,
      height: 600,
      latitude: 52.3,
      longitude: 5.387,
      zoom: 6
    },
    featureCollection: {
        features: []
    },
    popupInfo: null,
    mounted: false,
  };

  static defaultProps = {
    endpoint: 'https://waterinfo.rws.nl/api/point/latestmeasurements?parameterid=',
  };

  componentDidMount () {
    this.setState({mounted: true})
  }

  onChange = event => {
    const chosenMapType = event.target.value;
      fetch(`${this.props.endpoint}${chosenMapType}`)
        .then(resp => resp.json())
        .then(resp => {
          this.setState({
            featureCollection: resp,
            popupInfo: null
          });
        })
  };

  _renderMarker = (item, index) => {
    const crs = item.crs.properties.name;
    const [longitude, latitude] = proj4(crs).inverse(item.geometry.coordinates);

    const onClick = () => {
      this.setState({
        popupInfo: {
          latitude: latitude,
          longitude: longitude,
          name: item.properties.name,
          locationCode: item.properties.loctionCode
        }
      })
    };

    return (
      <Marker key={`marker-${index}`} longitude={longitude} latitude={latitude}>
        <Pin size={20} onClick={onClick}/>
      </Marker>
    );
  };

  _renderMarkers = () => {
    const {featureCollection} = this.state;
    return featureCollection.features.map(this._renderMarker)
  };

  _renderPopup() {
    const {popupInfo} = this.state;
    return (
      popupInfo && (
        <Popup
          tipSize={5}
          anchor="top"
          longitude={popupInfo.longitude}
          latitude={popupInfo.latitude}
          closeOnClick={false}
          onClose={() => this.setState({popupInfo: null})}
        >
          <MarkerInfo info={popupInfo} />
        </Popup>
      )
    );
  }

  _onViewStateChange = ({viewState, interactionState, oldViewState}) => {
    const {mounted} = this.state;
    if (mounted) {
      this.setState({viewState})
    }
  };

  render() {
    const {viewState} = this.state;
    return (
      <MapGL
        mapboxApiAccessToken = {process.env.REACT_APP_MAPBOX_API}
        {...viewState}
        onViewStateChange={this._onViewStateChange}
      >
        {this._renderMarkers()}
        {this._renderPopup()}

        <div className={"select-component"}>
          <TestSelect onChange={this.onChange}/>
        </div>

        {/*<div className="nav" style={navStyle}>*/}
        {/*  <NavigationControl onViewPortChange={()=>{}}/>*/}
        {/*</div>*/}

      </MapGL>
    );
  }
}

export default SimpleMap;