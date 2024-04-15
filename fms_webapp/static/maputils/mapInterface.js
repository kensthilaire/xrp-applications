
function showProgramMarkers( mapInfo, program, teamTypes, grants ) {
    
    var teamList = mapInfo.teamInfo.programs[program];
    var grant_filtered = true;
    var type_filtered = true;
    var org_filtered = true;
    var distance_filtered = true;

    var ref_distance = mapInfo.refDistance;

    console.log( 'Showing Markers For Program: ' + program );
    console.log( 'Team Types: ' + teamTypes );
    console.log( 'Grant Types: ' + grants );

    for ( var i=0; i<teamList.length; i++ ) {
        var team = mapInfo.teamInfo.teamData[teamList[i]];

        // if a grant filter has been specified, then check to see if
        // the team has been awarded one of the grant types.
        if ( grants.length ) {
            grant_filtered = false;
            if ( team.Grants ) {
                for ( var j=0; j<grants.length; j++ ) {
                    if ( team.Grants.indexOf(grants[j]) != -1 ) {
                        grant_filtered = true;
                        break;
                    }
                }
            }
        }

        // if the user specified a reference location and distance, enable 
        // only those markers for teams within that radius
        if ( ref_distance != 0 ) {
            distance_filtered = true;

            var center = mapInfo.map.getCenter();
            var location = new Object();
            location.lat = center.lat();
            location.lng = center.lng();

            var team_location = team.Geo_Location;
            var distance = calcDistanceFromPoint( location, team_location );
            if ( distance > ref_distance ) {
                distance_filtered = false;
            }
        }

        var display_marker = grant_filtered & type_filtered & org_filtered & distance_filtered;
        if ( team.marker ) {
            if ( display_marker )
                team.marker.setVisible(true);
            else
                team.marker.setVisible(false);
        }
    }
}

function hideProgramMarkers( mapInfo, program ) {
    var teamList = mapInfo.teamInfo.programs[program];

    console.log( 'Hiding Markers For Program: ' + program );
    for ( var i=0; i<teamList.length; i++ ) {
        var team = mapInfo.teamInfo.teamData[teamList[i]];

        if ( team.marker ) {
            team.marker.setVisible(false);
        }
    }
}

function showOrHideSchoolMarkers( mapInfo, program, visibility, levels, first_filters, programs ) {
    var schoolList = mapInfo.schoolInfo.programs[program];

    var ref_distance = mapInfo.refDistance;

    console.log( 'Hiding Markers For ' + program + ' Schools.' );
    for ( var i=0; i<schoolList.length; i++ ) {
        var school = mapInfo.schoolInfo.schoolData[schoolList[i]];
        var showMarker = visibility;
        var hasTeam;

        if ( levels && levels.length ) {
            var levelMatched = false;
            for ( var j=0; j<levels.length; j++ ) {
                if ( school.Target_Levels ) {
                    if ( school.Target_Levels.indexOf( levels[j] ) != -1 ) {
                        levelMatched = true;
                    }
                } else {
                    console.log( 'Target Levels not set for school: ' + school.School_Name );
                }
            } 
            if ( !levelMatched ) {
                showMarker = false;
            }
        }
        
        if ( programs && programs.length ) {
            var programMatched = false;
            var firstTeams = school.First_Teams;

            for ( var j=0; j<programs.length; j++ ) {
                if ( school.Target_Programs ) {
                    var targetPrograms = school.Target_Programs.split(',');
                    if ( targetPrograms ) {
                        for ( var k=0; k<targetPrograms.length; k++ ) {
                            if ( targetPrograms[k] == programs[j] ) {
                                if ( first_filters.length == 0 ) {
                                    programMatched = true;
                                } else if ( first_filters.indexOf( 'Yes' ) != -1 && firstTeams ) {
                                    for ( var l=0; l<firstTeams.length; l++ ) {
                                        if ( firstTeams[l].split('-')[0] == programs[j] ) {
                                            programMatched = true;
                                        }
                                    }
                                } else if ( first_filters.indexOf( 'No' ) != -1 ) {
                                    programMatched = true;
                                    if ( firstTeams ) {
                                        for ( var l=0; l<firstTeams.length; l++ ) {
                                            if ( firstTeams[l].split('-')[0] == programs[j] ) {
                                                programMatched = false;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                } else {
                    console.log( 'Target Programs not set for school: ' + school.School_Name ); 
                }
            } 
            if ( !programMatched )
                showMarker = false;
        } else {
            // process first filters to display only those schools that do or do not have first
            // teams based on the checkbox settings. 
            if ( first_filters && first_filters.length ) {
                if ( school.First_Teams )
                    hasTeam = 'Yes';
                else
                    hasTeam = 'No';
            
                if ( first_filters.indexOf( hasTeam ) == -1 )
                    showMarker = false;
            }
        }

        if ( showMarker ) {
            showMarker = setVisibilityFromRefDistance( mapInfo, school.Geo_Location );

            if ( school.marker ) {
                if ( showMarker ) {
                    school.marker.setVisible(visibility);
                } else {
                    school.marker.setVisible(false);
                }
            }
        } else {
            if ( school.marker ) {
                school.marker.setVisible(false);
            }
        }
    }
}

//
// Function: round()
//
// Simple little function that will round a value to the specified 
// number of decimal places. Used to round off the geo location 
// coordinates when detecting overlapping markers
//
function round(value, decimals) {
  return Number(Math.round(value+'e'+decimals)+'e-'+decimals);
}

//
// Function: mapLocation()
//
// This function was taken directly from the Google Maps API sample and adapted
// to insert a marker on the map for the specified entity and then store the 
// marker instance within the entity (Team, Event, or other) for later
// control

var current_info_window = null;

function getGeoLocation( mapInfo, teamInfo ) {
    var done = false;
    var attempt = 1;
    var geo_offset = 0.001;
    var geo_location = teamInfo.Geo_Location;

    if ( geo_location == null ) {
        return geo_location;
    }

    while ( !done ) {
        // Round off the geo location to a certain number of decimal places
        // so that we can accurately detect overlapping locations
        geo_location.lng = round( geo_location.lng, 7 );
        geo_location.lat = round( geo_location.lat, 7 );

        // Make a string of the geo location and then use that to look up into
        // the map of locations to see if we have already placed a marker at this location.
        geo_location_str = JSON.stringify(geo_location);
        if ( mapInfo[geo_location_str] == null ) {
            mapInfo[geo_location_str] = true;
            done = true;
        } else {
            // We have overlapping locations, so adjust the geo location by the offset, 
            // circling around the actual location for the team so that the markers are
            // clustered around the actual location in a way that allows them to be viewed
            // when zooming in on the map
            geo_location = teamInfo.Geo_Location;
            switch( attempt ) {
                case 1:
                    geo_location.lat += geo_offset;
                    break;
                case 2:
                    geo_location.lng += geo_offset;
                    break;
                case 3:
                    geo_location.lat -= geo_offset;
                    break;
                case 4:
                    geo_location.lng -= geo_offset;
                    break;
                case 5:
                    geo_location.lat += geo_offset;
                    geo_location.lng += geo_offset;
                    break;
                case 6:
                    geo_location.lat -= geo_offset;
                    geo_location.lng += geo_offset;
                    break;
                case 7:
                    geo_location.lat -= geo_offset;
                    geo_location.lng -= geo_offset;
                    break;
                case 8:
                    geo_location.lat += geo_offset;
                    geo_location.lng -= geo_offset;
                    break;
                default:
                    // create the next level of the ring around the base location
                    geo_offset += geo_offset;
                    attempt = 0;
                    // if we have gone around the same location 10 times, then call it quits and 
                    // allow the overlap
                    if ( geo_offset > (geo_offset*10) ) {
                        console.log( 'Cannot map the location after 10 cycles!');
                        done = true;
                    }
                    break;
            }
            attempt += 1;
        }
    }
    return geo_location;
}

function addInfoWindow( marker, infoString ) {
    var infoWindow = new google.maps.InfoWindow({ content: infoString });
    google.maps.event.addListener(marker, 'click', function () {
                                    if ( current_info_window == null ) {
                                        infoWindow.open(map, marker);
                                        current_info_window = infoWindow;
                                    } else {
                                        if ( infoWindow == current_info_window ) {
                                            current_info_window.close();
                                            current_info_window = null;
                                        } else {
                                            current_info_window.close();
                                            infoWindow.open(map, marker);
                                            current_info_window = infoWindow;
                                        }
                                    }
                                  });

    google.maps.event.addListener(marker, 'dblclick', function () {
                                      marker.map.setCenter(marker.position);
                                      marker.map.setZoom(12);
                                  });
    return infoWindow;
}

function mapTeamLocation(team, mapInfo) {

    var resultsMap = mapInfo.map;
    var icon = mapInfo.teamInfo.icons[team.Program.toLowerCase()];

    var geo_location = getGeoLocation( mapInfo, team );
    if ( geo_location == null ) {
        console.log( 'No Geo Location for ' + team.Program + ' Team ' + team.Team_Number );
        return;
    }

    var marker = new google.maps.Marker({
                                        map: resultsMap,
                                        position: geo_location,
                                        icon: icon
                                    });
    if ( !marker ) {
        console.log( "Error creating marker for " + team.Team_Number );        
    }

    var infoString = "";
            
    infoString = '<b>' + team.Program + ' Team ' + team.Team_Number + ', ' + team.Team_Name + '</b>.';
    infoString += '<br>' + 'From ' + team.Organization + '.';
    infoString += '<br>' + 'Located In ' + team.City + ', ' + team.State;

    var infoWindow = addInfoWindow( marker, infoString );

    team.marker = marker;
    team.marker.setVisible(false);
    team.infoWindow = infoWindow;

}

//
// Function: mapTeams()
//
// This function will loop through the list of defined teams and plot a marker on the map
// for the team.
//
function mapTeams( mapInfo ) {

    if ( mapInfo.teamsLoaded == false ) {
        console.log( "Pausing 1 second for teams to load" );
        setTimeout(function(){ mapTeams(mapInfo) }, 1000);
    } else {

        for ( var i=0; i<mapInfo.teamInfo.programTypes.length; i++ ) {
            var program = mapInfo.teamInfo.programs[mapInfo.teamInfo.programTypes[i]];

            console.log( 'Mapping ' + mapInfo.teamInfo.programTypes[i] + ' Teams' );

            for ( var j=0; j<program.length; j++ ) {
                var teamInfo = mapInfo.getTeam( program[j] );

                // Only map the registered teams, otherwise we'll have a ton of stale unregistered teams
                if ( teamInfo.Registered == 'Yes' ) {
                    mapTeamLocation( teamInfo, mapInfo );
                }
            }
        }

        mapInfo.teamsMapped = true;
        console.log( "Teams Mapped Successfully" );
    }
}

function setVisibilityFromRefDistance( mapInfo, location ) {
    var ref_distance = mapInfo.refDistance;
    var display_marker = true;

    // if the user specified a reference location and distance, enable 
    // only those markers for teams within that radius
    if ( ref_distance != 0 ) {
        var center = mapInfo.map.getCenter();
        var ref_location = new Object();
        ref_location.lat = center.lat();
        ref_location.lng = center.lng();

        var distance = calcDistanceFromPoint( ref_location, location );
        if ( distance > ref_distance ) {
            display_marker = false;
        }
    }

    return display_marker;
}

function showOrHideClasspackMarkers( mapInfo, visibility ) {
    var classpackInfo = mapInfo.classpackInfo;

    console.log( 'Showing/Hiding Markers For Classpacks.' );
    for ( var i=0; i<classpackInfo.classpackData.length; i++ ) {
        var classpack = classpackInfo.classpackData[i];
        var display_marker = setVisibilityFromRefDistance( mapInfo, classpack.Geo_Location );

        if ( classpack.marker ) {
            if ( display_marker ) {
                classpack.marker.setVisible(visibility);
            } else {
                classpack.marker.setVisible(false);
            }
        }
    }
}

function mapClasspackLocation(classpack, mapInfo) {

    var resultsMap = mapInfo.map;
    var icon = mapInfo.classpackInfo.icon;

    var geo_location = getGeoLocation( mapInfo, classpack );
    if ( geo_location == null ) {
        console.log( 'No Geo Location for Classpack ' + classpack.Team_Number );
        return;
    }

    var marker = new google.maps.Marker({
                                        map: resultsMap,
                                        position: geo_location,
                                        icon: icon
                                    });
    if ( !marker ) {
        console.log( "Error creating marker for " + classpack.Team_Number );        
    }

    var infoString = "";
            
    infoString = '<b>Classpack ' + classpack.Team_Number + '</b>.';
    infoString += '<br>' + 'From ' + classpack.Organization + '.';
    infoString += '<br>' + 'Located In ' + classpack.City + ', ' + classpack.State;

    var infoWindow = addInfoWindow( marker, infoString );

    classpack.marker = marker;
    classpack.marker.setVisible(false);
    classpack.infoWindow = infoWindow;

}

//
// Function: mapClasspacks()
//
// This function will loop through the list of defined classpacks and plot a marker on the map
// for the classpack.
//
function mapClasspacks( mapInfo ) {

    if ( mapInfo.classpacksLoaded == false ) {
        console.log( "Pausing 1 second for classpacks to load" );
        setTimeout(function(){ mapClasspacks(mapInfo) }, 1000);
    } else {

        for ( var i=0; i<mapInfo.classpackInfo.classpackData.length; i++ ) {
            var classpackElem = mapInfo.classpackInfo.classpackData[i];

            // Only map the registered teams, otherwise we'll have a ton of stale unregistered teams
            if ( classpackElem.Registered == 'Yes' ) {
                mapClasspackLocation( classpackElem, mapInfo );
            }
        }

        mapInfo.classpacksMapped = true;
        console.log( "Classpacks Mapped Successfully" );
    }
}

function mapSchoolLocation(school, mapInfo) {

    var resultsMap = mapInfo.map;
    var icon = mapInfo.schoolInfo.icons[school.Group_Id.toLowerCase()];

    var geo_location = getGeoLocation( mapInfo, school );
    if ( geo_location == null ) {
        console.log( 'No Geo Location for ' + school.School_Name );
        return;
    }

    var marker = new google.maps.Marker({
                                        map: resultsMap,
                                        position: geo_location,
                                        icon: icon
                                    });
    if ( !marker ) {
        console.log( "Error creating marker for " + school.School_Name );        
    }

    var infoString = "";
            
    infoString = '<b>' + school.School_Name + '</b>.';
    infoString += '<br>' + 'From ' + school.City + ', ' + school.State + '.';
    infoString += '<br>' + school.Sch_Type_Desc + ' serving grades ' + school.Grade_Span + '.';

    if ( school.First_Teams ) {
        infoString += '<br>Teams: ' + school.First_Teams.join() + '.';
    }
        
    var infoWindow = addInfoWindow( marker, infoString );

    school.marker = marker;
    school.marker.setVisible(false);
    school.infoWindow = infoWindow;

}

//
// Function: mapSchools()
//
// This function will loop through the list of defined schools and plot a marker on the map
// for each school.
//
function mapSchools( mapInfo ) {

    if ( mapInfo.schoolsLoaded == false ) {
        console.log( "Pausing 1 second for schools to load" );
        setTimeout(function(){ mapSchools(mapInfo) }, 1000);
    } else {

        for ( var i=0; i<mapInfo.schoolInfo.programTypes.length; i++ ) {
            var program = mapInfo.schoolInfo.programs[mapInfo.schoolInfo.programTypes[i]];

            console.log( 'Mapping ' + mapInfo.schoolInfo.programTypes[i] + ' Schools' );

            for ( var j=0; j<program.length; j++ ) {
                var schoolInfo = mapInfo.getSchool( program[j] );
                mapSchoolLocation( schoolInfo, mapInfo );
            }
        }

        mapInfo.schoolsMapped = true;
        console.log( "Schools Mapped Successfully" );
    }
}

//
// Function: mapCounties()
//
//
function mapCounties( mapInfo ) {

    if ( mapInfo.countiesLoaded == false ) {
        console.log( "Pausing 1 second for counties to load" );
        setTimeout(function(){ mapCounties(mapInfo) }, 1000);
    } else {
        mapInfo.countyInfo.mapCounty();
    }
}

//
// Function: showCounty()
//
//
function showCounty( mapInfo, showControl, countyName ) {

    if ( mapInfo.countiesLoaded == false ) {
        console.log( "Pausing 1 second for counties to load" );
        setTimeout(function(){ showCounty(mapInfo, showControl, countyName) }, 1000);
    } else {
        mapInfo.countyInfo.showCounty( mapInfo.map, showControl, countyName );
    }
}

//
// Function: mapCtes()
//
// This function will loop through the list of defined CTE centers and plot a marker on the map
// for each center.
//
function mapCtes( mapInfo ) {

    if ( mapInfo.ctesLoaded == false ) {
        console.log( "Pausing 1 second for ctes to load" );
        setTimeout(function(){ mapCtes(mapInfo) }, 1000);
    } else {

        for ( var i=0; i<mapInfo.cteInfo.cteData.length; i++ ) {
            var cte = mapInfo.cteInfo.cteData[i];

            mapCteLocation( cte, mapInfo );
        }

        mapInfo.ctesMapped = true;
        console.log( "Ctes Mapped Successfully" );
    }
}

function showOrHideCteMarkers( mapInfo, visibility ) {
    var cteInfo = mapInfo.cteInfo;

    console.log( 'Hiding Markers For Ctes.' );
    for ( var i=0; i<cteInfo.cteData.length; i++ ) {
        var cte = cteInfo.cteData[i];

        var display_marker = setVisibilityFromRefDistance( mapInfo, cte.Geo_Location );
        if ( cte.marker ) {
            if ( display_marker ) {
                cte.marker.setVisible(visibility);
            } else {
                cte.marker.setVisible(false);
            }
        }
    }
}

function mapCteLocation(cte, mapInfo) {

    var resultsMap = mapInfo.map;
    var icon = mapInfo.cteInfo.icon;

    var geo_location = getGeoLocation( mapInfo, cte );
    if ( geo_location == null ) {
        console.log( 'No Geo Location for ' + cte.Name );
        return;
    }

    var marker = new google.maps.Marker({
                                        map: resultsMap,
                                        position: geo_location,
                                        icon: icon
                                    });
    if ( !marker ) {
        console.log( "Error creating marker for " + cte.Name );        
    }

    var infoString = "";
            
    infoString = '<b>' + cte.Name + '</b>.';

    var infoWindow = addInfoWindow( marker, infoString );

    cte.marker = marker;
    cte.marker.setVisible(false);
    cte.infoWindow = infoWindow;

}

function showOrHideUnitMarkers( mapInfo, program, visibility ) {
    var unitList = mapInfo.unitInfo.programs[program];

    if ( visibility )
        console.log( 'Showing Markers For ' + program + ' Units.' );
    else
        console.log( 'Hiding Markers For ' + program + ' Units.' );

    for ( var i=0; i<unitList.length; i++ ) {
        var unit = mapInfo.unitInfo.unitData[unitList[i]];

        var display_marker = setVisibilityFromRefDistance( mapInfo, unit.Geo_Location );
        if ( unit.marker ) {
            if ( display_marker ) {
                unit.marker.setVisible(visibility);
            } else {
                unit.marker.setVisible(false);
            }
        }
    }
}

function mapUnitLocation(unit, mapInfo) {

    var resultsMap = mapInfo.map;
    var icon = mapInfo.unitInfo.icons[unit.Program.toLowerCase()];

    var geo_location = getGeoLocation( mapInfo, unit );
    if ( geo_location == null ) {
        console.log( 'No Geo Location for ' + unit.Name );
        return;
    }

    var marker = new google.maps.Marker({
                                        map: resultsMap,
                                        position: geo_location,
                                        icon: icon
                                    });
    if ( !marker ) {
        console.log( "Error creating marker for " + unit.Name );        
    }

    var infoString = "";
            
    infoString = '<b>' + unit.Unit + '</b>';
    infoString += '<br>' + 'Chartered By  ' + unit.Name;
    infoString += '<br>' + 'From ' + unit.City + ', ' + unit.State + '.';

    var infoWindow = addInfoWindow( marker, infoString );

    unit.marker = marker;
    unit.marker.setVisible(false);
    unit.infoWindow = infoWindow;

}

//
// Function: mapUnits()
//
// This function will loop through the list of defined units and plot a marker on the map
// for each unit.
//
function mapUnits( mapInfo ) {

    if ( mapInfo.unitsLoaded == false ) {
        console.log( "Pausing 1 second for units to load" );
        setTimeout(function(){ mapUnits(mapInfo) }, 1000);
    } else {

        for ( var i=0; i<mapInfo.unitInfo.programTypes.length; i++ ) {
            var program = mapInfo.unitInfo.programs[mapInfo.unitInfo.programTypes[i]];

            console.log( 'Mapping ' + mapInfo.unitInfo.programTypes[i] + ' Units' );

            for ( var j=0; j<program.length; j++ ) {
                var unitInfo = mapInfo.getUnit( program[j] );
                mapUnitLocation( unitInfo, mapInfo );
            }
        }

        mapInfo.unitsMapped = true;
        console.log( "Units Mapped Successfully" );
    }
}

