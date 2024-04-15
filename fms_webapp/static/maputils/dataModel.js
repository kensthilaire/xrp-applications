
function MapData() {
    this.teamsLoaded = false;
    this.teamsMapped = false;
    this.teamInfo = new TeamInfo();

    this.classpacksLoaded = false;
    this.classpacksMapped = false;
    this.classpackInfo = new ClasspackInfo();

    this.schoolsLoaded = false;
    this.schoolsMapped = false;
    this.schoolInfo = new SchoolInfo();

    this.ctesLoaded = false;
    this.ctesMapped = false;
    this.cteInfo = new CteInfo();

    this.unitsLoaded = false;
    this.unitsMapped = false;
    this.unitInfo = new UnitInfo();

    this.countiesLoaded = false;
    this.countyInfo = new CountyInfo();

    this.getTeam = function( teamNumber ) { return this.teamInfo.getTeam( teamNumber ); }
    this.getTeamMarker = function( teamNumber ) { return this.teamInfo.getMarker( teamNumber ); }
    this.getSchool = function( schoolId ) { return this.schoolInfo.getSchool( schoolId ); }
    this.getUnit = function( unitId ) { return this.unitInfo.getUnit( unitId ); }

    this.loadData = function( region, season ) {
        this.season = season;
        this.region = region;
        this.teamInfo.loadData(this);
        this.classpackInfo.loadData(this);
        this.schoolInfo.loadData(this);
        this.countyInfo.loadData(this);
        this.cteInfo.loadData(this);
        this.unitInfo.loadData(this);
    }

    this.geoLocations = new Object();
    this.currLocation = '';
    this.currZoom = 0;
    this.refDistance = 0;
}

function TeamInfo() {

    this.programTypes = ['flljr','fll','ftc','frc'];

    this.programs = new Object();
    this.programs.flljr = [];
    this.programs.fll = [];
    this.programs.ftc = [];
    this.programs.frc = [];

    this.teamData = [];
    this.teamAttrs = [];

    // initialize the marker icons for each of the programs
    this.icons = new Object();
    this.icons.flljr = '../static/images/green-dot.png';
    this.icons.fll = '../static/images/red-dot.png';
    this.icons.ftc = '../static/images/orange-dot.png';
    this.icons.frc = '../static/images/blue-dot.png';

    this.getTeam = function( teamNumber ) { return this.teamData[ teamNumber ]; } 

    this.setMarker = function(teamNumber, marker) {
                            team = getTeam( teamNumber );
                            team.marker = marker;
                     }
    this.getMarker = function(teamNumber) {
                            team = getTeam( teamNumber );
                            return team.marker;
                     }

    this.loadData = function(mapInfo) { LoadTeamDataFromServer(mapInfo, this); }
}

function ClasspackInfo() {

    this.loadData = function(mapInfo) { LoadClasspackDataFromServer(mapInfo, this); }
    this.classpackData = [];
    this.classpackAttrs = [];
    this.getClasspacks = function() { return this.classpackData; }

    this.icon = '../static/images/pink-dot.png';
}

function SchoolInfo() {

    this.programTypes = ['pub','prv'];

    this.programs = new Object();
    this.programs.pub = [];
    this.programs.prv = [];

    this.schoolData = [];
    this.schoolAttrs = [];

    // initialize the marker icons for each school type
    this.icons = new Object();
    this.icons.pub = '../static/images/ltblue-dot.png';
    this.icons.prv = '../static/images/purple-dot.png';

    this.getSchool = function( schoolId ) { return this.schoolData[ schoolId ]; } 

/*
    this.setMarker = function(schoolId, marker) {
                            school = getSchool( schoolId );
                            school.marker = marker;
                     }
    this.getMarker = function(schoolId) {
                            school = getSchool( schoolId );
                            return school.marker;
                     }
*/

    this.loadData = function(mapInfo) { LoadSchoolDataFromServer(mapInfo, this); }
}

function CountyInfo() {

    this.loadData = function(mapInfo) { LoadCountyDataFromServer(mapInfo, this); }

    this.countyData = [];

    this.getCounties = function() { return this.countyData; }

    this.mapCounty = function(countyName) {
        var overlay_colors = [ '#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#00FFFF', '#FF00FF', '#FF7F00', '#7F00FF' ];

        if ( countyName == null ) {
            for ( var i=0;i<this.countyData.length;i++ ) {
                var overlay_coordinates = new Array();
                var geo_coordinates = this.countyData[i].geometry.split(' ');
                for ( var j=0;j<geo_coordinates.length;j++ ) {
                    var geo_values = geo_coordinates[j].split(',');
                    overlay_coordinates.push( { lat: parseFloat(geo_values[1]), lng: parseFloat(geo_values[0]) } );
                }

                var overlay_color = overlay_colors[ i % overlay_colors.length ];
                this.countyData[i].overlay = new google.maps.Polygon({
                    paths: overlay_coordinates,
                    strokeColor: overlay_color,
                    strokeOpacity: 0.0,
                    strokeWeight: 2,
                    fillColor: overlay_color,
                    fillOpacity: 0.35 });
            }
        }
    }

    this.showCounty = function(map, showControl, countyName) {
        var counties = this.countyData;
        var county=null;
        for ( var i=0;i<counties.length;i++ ) {
            if ( countyName == null ) {
                if ( showControl == true )
                    counties[i].overlay.setMap( map );
                else
                    counties[i].overlay.setMap( null );
            } else if ( counties[i].name == countyName ) {
                if ( showControl == true )
                    counties[i].overlay.setMap( map );
                else
                    counties[i].overlay.setMap( null );
                break;
            }
        }
    }
}

function CteInfo() {

    this.loadData = function(mapInfo) { LoadCteDataFromServer(mapInfo, this); }
    this.cteData = [];
    this.getCtes = function() { return this.cteData; }

    this.icon = '../static/images/yellow-dot.png';
}

function UnitInfo() {

    this.loadData = function(mapInfo) { LoadUnitDataFromServer(mapInfo, this); }
    this.unitData = [];
    this.numUnits = 0;
    this.getUnits = function() { return this.unitData; }

    this.programTypes = ['troop','pack', 'crew', 'post'];

    this.getUnit = function( unitId ) { return this.unitData[ unitId ]; } 

    this.programs = new Object();
    this.programs.troop = [];
    this.programs.pack = [];
    this.programs.crew = [];
    this.programs.post = [];

    // initialize the marker icons for each school type
    this.icons = new Object();
    this.icons.troop = '../static/images/red-dot.png';
    this.icons.pack = '../static/images/blue-dot.png';
    this.icons.crew = '../static/images/green-dot.png';
    this.icons.post = '../static/images/purple-dot.png';

}

function GeoLocation( lat, lng ) {
    this.lat = lat;
    this.lng = lng;
}

// function will load the team data from the JSON formatted string variable that is generated
// by an external program and stored as a JavaScript file.
function LoadTeamData( mapInfo, teamInfo ) {
    var mapTeamData = JSON.parse(map_data_for_teams);

    /*
    for ( var i=0;i<mapTeamData.length; i++ ) {
        var team = mapTeamData[i];

        teamInfo.programs[team.Program.toLowerCase()].push(team.Program.toLowerCase()+team.Team_Number);
        teamInfo.teamData[team.Program.toLowerCase()+team.Team_Number]=team;
    }
    */

    for( var program in mapTeamData.programs) {
        var program_data = mapTeamData.programs[program];

        console.log( 'Processing ' + program );

        for ( var team in program_data ) {
            var team_data = program_data[team];
            console.log( 'Loading Team ' + team );
            teamInfo.programs[team_data.Program.toLowerCase()].push(team_data.Program.toLowerCase()+team_data.Team_Number);
            teamInfo.teamData[team_data.Program.toLowerCase()+team_data.Team_Number]=team_data;
        }
    }

    mapInfo.teamsLoaded = true;
}

function LoadTeamDataFromServer( mapInfo, teamInfo ) {

    function LoadTeamDataInRegion( mapInfo, region_index, team_entry_attr_map ) {

        var jqxhr = $.getJSON( '/api/teams/?region=' + mapInfo.region[region_index] + '&season=' + mapInfo.season, function(json_data) {
            console.log("Teams Loaded Success");
            for (var i=0;i<json_data.length;i++) {
                var team_data = json_data[i].info;
                var program = json_data[i].program.toLowerCase();

                teamInfo.programs[program].push(program+team_data.Team_Number);
                teamInfo.teamData[program+team_data.Team_Number]=team_data;

                // generate a table of all the attributes that appear in the team entry, deriving the
                // table from the actual info block returned for the teams.
                for ( var key in json_data[i].info ) {
                    team_entry_attr_map[key] = true;
                }
            }
            region_index += 1;
            if ( region_index < mapInfo.region.length ) {
                LoadTeamDataInRegion( mapInfo, region_index, team_entry_attr_map );
            } else {
                teamInfo.teamAttrs = Object.keys(team_entry_attr_map);
                mapInfo.teamsLoaded = true;
            }
        });
    }

    var region_index = 0;
    var team_entry_attr_map = [];
    LoadTeamDataInRegion( mapInfo, region_index, team_entry_attr_map );
}

function LoadClasspackDataFromServer( mapInfo, classpackInfo ) {

    function LoadClasspackDataInRegion( mapInfo, region_index, classpack_entry_attr_map ) {

        var jqxhr = $.getJSON( '/api/classpacks/?region=' + mapInfo.region[region_index] + '&season=' + mapInfo.season, function(json_data) {
            console.log("Classpacks Loaded Success");
            for (var i=0;i<json_data.length;i++) {
                classpackInfo.classpackData[i]=json_data[i].info;

                // generate a table of all the attributes that appear in the classpack entry, deriving the
                // table from the actual info block returned for the classpacks.
                for ( var key in json_data[i].info ) {
                    classpack_entry_attr_map[key] = true;
                }
            }
            region_index += 1;
            if ( region_index < mapInfo.region.length ) {
                LoadClasspackDataInRegion( mapInfo, region_index, classpack_entry_attr_map );
            } else {
                classpackInfo.classpackAttrs = Object.keys(classpack_entry_attr_map);
                mapInfo.classpacksLoaded = true;
            }
        });
    }

    var region_index = 0;
    var classpack_entry_attr_map = [];
    LoadClasspackDataInRegion( mapInfo, region_index, classpack_entry_attr_map );
}

function LoadSchoolDataFromServer( mapInfo, schoolInfo ) {

    function LoadSchoolDataInRegion( mapInfo, region_index, school_entry_attr_map ) {
        var jqxhr = $.getJSON( '/api/schools/' + '?region=' + mapInfo.region[region_index], function(json_data) {
            console.log("Schools Loaded Success");
            for (var i=0;i<json_data.length;i++) {
                var school_data = json_data[i].info;
                var program = json_data[i].info.Group_Id.toLowerCase();
    
                schoolInfo.programs[program].push(school_data.Sch_Id);
                schoolInfo.schoolData[school_data.Sch_Id]=school_data;

                json_data[i].info['Admin_Name'] = json_data[i].info['Fname'] + ' ' + json_data[i].info['Lname'];

                // generate a table of all the attributes that appear in the school entry, deriving the
                // table from the actual info block returned for the schools.
                for ( var key in json_data[i].info ) {
                    school_entry_attr_map[key] = true;
                }
            }
            region_index += 1;
            if ( region_index < mapInfo.region.length ) {
                LoadSchoolDataInRegion( mapInfo, region_index, school_entry_attr_map );
            } else {
                schoolInfo.schoolAttrs = Object.keys(school_entry_attr_map);
                mapInfo.schoolsLoaded = true;
            }
        });
    }
    var region_index = 0;
    var school_entry_attr_map = [];

    LoadSchoolDataInRegion( mapInfo, region_index, school_entry_attr_map );
}

function LoadCteDataFromServer( mapInfo, cteInfo ) {

    function LoadCteDataInRegion( mapInfo, region_index ) {
        var jqxhr = $.getJSON( '/api/ctes/' + '?region=' + mapInfo.region[region_index], function(json_data) {
            console.log("Ctes Loaded Success");
            for (var i=0;i<json_data.length;i++) {
                cteInfo.cteData[i] = json_data[i].info;
            }
            region_index += 1;
            if ( region_index < mapInfo.region.length ) {
                LoadCteDataInRegion( mapInfo, region_index );
            } else {
                mapInfo.ctesLoaded = true;
            }
        });
    }

    var region_index = 0;
    LoadCteDataInRegion( mapInfo, region_index );
}

function LoadUnitDataFromServer( mapInfo, unitInfo ) {

    function LoadUnitDataInRegion( mapInfo, region_index ) {
        var jqxhr = $.getJSON( '/api/units/' + '?region=' + mapInfo.region[region_index], function(json_data) {
            console.log("Units Loaded Success");
            for (var i=0;i<json_data.length;i++) {
                var unit_data = json_data[i].info;
                var program = json_data[i].info.Program.toLowerCase();

                unitInfo.programs[program].push(unit_data.Unit);
                unitInfo.unitData[unit_data.Unit]=unit_data;
            }
            unitInfo.numUnits += json_data.length;

            region_index += 1;
            if ( region_index < mapInfo.region.length ) {
                LoadUnitDataInRegion( mapInfo, region_index );
            } else {
                mapInfo.unitsLoaded = true;
            }
        });
    }

    var region_index = 0;
    LoadUnitDataInRegion( mapInfo, region_index );
}

function LoadCountyDataFromServer( mapInfo, countyInfo ) {

    function LoadCountyDataInRegion( mapInfo, region_index ) {
        var jqxhr = $.getJSON( '/api/counties/' + '?region=' + mapInfo.region, function(json_data) {
            console.log("Counties Loaded Success");
            for (var i=0;i<json_data.length;i++) {
                countyInfo.countyData[i] = json_data[i];
            }

            region_index += 1;
            if ( region_index < mapInfo.region.length ) {
                LoadCountyDataInRegion( mapInfo, region_index );
            } else {
                mapInfo.countiesLoaded = true;
            }
        });
    }

    var region_index = 0;
    LoadCountyDataInRegion( mapInfo, region_index );
}

// test function to load some dummy data to validate the data model and map functions
function LoadTeamDummyData( mapInfo, teamInfo ) {
    // FRC team
    team = new Object();
    team.Team_Number = '1073';
    team.Program = 'FRC';
    team.Organization = 'Hollis Brookline High School';
    team.Address = '24 Cavalier Court, Hollis, NH';
    team.Geo_Location = new GeoLocation( 42.7272362, -71.59613279999999 );
    team.District = 'SAU 41';

    teamInfo.programs[team.Program.toLowerCase()].push(team.Program.toLowerCase()+team.Team_Number);
    teamInfo.teamData[team.Program.toLowerCase()+team.Team_Number]=team;
    
    mapInfo.teamsLoaded = true;
}


