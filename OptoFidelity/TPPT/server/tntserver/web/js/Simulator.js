/*

Robot simulator
(c) Optofidelity Oy 2017, 2018

*/

__MODEL_DEBUG__ = false;
// model_debug sets 0.5 opacity to objects and shows object coordinate system arrows


__OUTLINE_RENDER__ = false;
// render outlines with black lines for clearer view

var engine, tnt, simulator;
var FPS = 30;

    function getDistortionShaderDefinition()
    {
        return {

            uniforms: {
                "tDiffuse":         { type: "t", value: null },
                "strength":         { type: "f", value: 0 },
                "height":           { type: "f", value: 1 },
                "aspectRatio":      { type: "f", value: 1 },
                "cylindricalRatio": { type: "f", value: 1 }
            },

            vertexShader: [
                "uniform float strength;",          // s: 0 = perspective, 1 = stereographic
                "uniform float height;",            // h: tan(verticalFOVInRadians / 2)
                "uniform float aspectRatio;",       // a: screenWidth / screenHeight
                "uniform float cylindricalRatio;",  // c: cylindrical distortion ratio. 1 = spherical

                "varying vec3 vUV;",                // output to interpolate over screen
                "varying vec2 vUVDot;",             // output to interpolate over screen

                "void main() {",
                    "gl_Position = projectionMatrix * (modelViewMatrix * vec4(position, 1.0));",

                    "float scaledHeight = strength * height;",
                    "float cylAspectRatio = aspectRatio * cylindricalRatio;",
                    "float aspectDiagSq = aspectRatio * aspectRatio + 1.0;",
                    "float diagSq = scaledHeight * scaledHeight * aspectDiagSq;",
                    "vec2 signedUV = (2.0 * uv + vec2(-1.0, -1.0));",

                    "float z = 0.5 * sqrt(diagSq + 1.0) + 0.5;",
                    "float ny = (z - 1.0) / (cylAspectRatio * cylAspectRatio + 1.0);",

                    "vUVDot = sqrt(ny) * vec2(cylAspectRatio, 1.0) * signedUV;",
                    "vUV = vec3(0.5, 0.5, 1.0) * z + vec3(-0.5, -0.5, 0.0);",
                    "vUV.xy += uv;",
                "}"
            ].join("\n"),

            fragmentShader: [
                "uniform sampler2D tDiffuse;",      // sampler of rendered scene?s render target
                "varying vec3 vUV;",                // interpolated vertex output data
                "varying vec2 vUVDot;",             // interpolated vertex output data

                "void main() {",
                    "vec3 uv = dot(vUVDot, vUVDot) * vec3(-0.5, -0.5, -1.0) + vUV;",
                    "gl_FragColor = texture2DProj(tDiffuse, uv);",
                "}"
            ].join("\n")

        };
    }

	function Begin()
		{
		engine = new Engine();

		simulator = new Simulator();

		initCommunication();
		}


	var INTERSECTED;


	function Probe( name, parent_name )
		{
		this.name = name;
		this.parent_name = parent_name;
		}

	Probe.prototype.read = function()
		{
		var parent = engine.objects[ this.parent_name ];

		//
		// Create a vector starting from parent object position and pointing to local Z direction
		var p0 = new THREE.Vector3( 0, 0, 0 );
		var p1 = new THREE.Vector3( 0, 0, 1 );

		//  translate to world
		p0 = parent.localToWorld( p0 );
		p1 = parent.localToWorld( p1 );
		var dir = new THREE.Vector3( p1.x - p0.x, p1.y - p0.y, p1.z - p0.z );

		var raycaster = new THREE.Raycaster( p0, dir );
		var intersects = raycaster.intersectObjects( engine.collision_objects );
		if( intersects.length > 0 )
			{
			var distance = 100000000;
			for( var i=0; i<intersects.length; i++ )
				{
				var d = intersects[ i ].distance;
				if( d < distance ) distance = d;
				}
			return distance;
			}
		return -1;
		}


	function DynamicTexture( w, h )
		{
		var canvas = document.createElement( "canvas" );
		canvas.width = w;
		canvas.height = h;
		var c = canvas.getContext("2d");
		c.fillStyle = "#FFFFFF";
		c.fillRect( 0, 0, w, h );

		var texture = new THREE.CanvasTexture( canvas );
		var material = new THREE.MeshBasicMaterial( { map: texture } );

		this.canvas = canvas;
		this.texture = texture;
		this.material = material;
		this.drawColor = "black";
		}

	DynamicTexture.prototype.release = function()
	    {
	    THREE.freeObjectRecursive
	    }

	DynamicTexture.prototype.draw = function( program, scale )
		{
		//
		// Command must be separated from parameters by a space
		// parameters must be separated by space
		// Commands are separated from each other by ;

		// Example:
		// 	dt.draw( "color orange; cls; color black; line 0 0 100 100; color white; line 100 0 0 100;" );
		//

		console.log( "DynamicTexture draw scale==", scale );

		var canvas = this.canvas;
		var c = canvas.getContext( "2d" );
		var w = canvas.width;
		var h = canvas.height;

		var lines = program.split( ';' );
		for( var i=0; i<lines.length; i++ )
			{
			var line = lines[ i ].trim();

    		//console.log("   draw '" + line + "'");

			var params = line.split( ' ' );
			var cmd = params[ 0 ];
			params.splice( 0, 1 );

			if( cmd == 'color' )
				{
				this.drawColor = params[ 0 ];
				}

			else if( cmd == 'cls' )
				{
				c.fillStyle = this.drawColor;
				c.fillRect( 0, 0, w, h );
				}

			else if( cmd == 'line' )
				{
				var x0 = params[ 0 ] * scale;
				var y0 = params[ 1 ] * scale;
				var x1 = params[ 2 ] * scale;
				var y1 = params[ 3 ] * scale;

				c.beginPath();
				c.moveTo( x0, y0 );
				c.lineTo( x1, y1 );
				c.strokeStyle = this.drawColor;
				c.stroke();
				c.closePath();
				}

			else if( cmd == 'circle' )
				{
				// params : x, y, radius, (line width or filled==0)
				var pie = false
				var x = params[ 0 ] * scale;
				var y = params[ 1 ] * scale;
				var r = params[ 2 ] * scale;

				var w = 1;
				var a0 = 0;
				var a1 = 2 * Math.PI;
				if( params.length > 3 ) w = params[ 3 ] * scale;
				if( params.length > 4 ) a0 = params[ 4 ] * Math.PI / 180.0;
				if( params.length > 5 ) a1 = params[ 5 ] * Math.PI / 180.0;
				if( params.length > 4 )
				    {
				    pie = true;
				    }

				c.save();
				c.beginPath();

				if( pie ) c.moveTo( x, y );

				c.arc( x, y, r, a0, a1 );

				if( pie ) c.lineTo( x, y );

				c.fillStyle = this.drawColor;
				c.strokeStyle = this.drawColor;

				if( w == 0 )
					{
					c.fill();
					}
				else
					{
					c.lineWidth = w;
					c.stroke();
					}
				c.closePath();

				c.restore();
				}

			else if( cmd == 'rect' )
				{
				// params : x1, y1, x2, y2, (line width or filled==0)
				var x0 = params[ 0 ] * scale;
				var y0 = params[ 1 ] * scale;
				var x1 = params[ 2 ] * scale;
				var y1 = params[ 3 ] * scale;
				var w = 1;
				if( params.length > 4 ) w = params[ 4 ] * scale;

				c.save();
				c.beginPath();

				c.rect( x0, y0, x1-x0, y1-y0 );

				c.fillStyle = this.drawColor;
				c.strokeStyle = this.drawColor;

				if( w == 0 )
					{
					c.fill();
					}
				else
					{
					c.lineWidth = w;
					c.stroke();
					}
				c.closePath();

				c.restore();
				}

			else if( cmd == 'bitmap' )
			    {
			    // params : x1, y1, x2, y2, base64 encoded image (jpeg, png, etc.)
				var x0 = params[ 0 ] * scale;
				var y0 = params[ 1 ] * scale;
				var x1 = params[ 2 ] * scale;
				var y1 = params[ 3 ] * scale;
				var image_data = params[ 4 ];

				img = new Image();
				img.x0 = x0;
				img.y0 = y0;
				img.x1 = x1;
				img.y1 = y1;
				img.onload = this.imageLoaded.bind(this);
				img.src = "data:image/png;base64," + image_data;
                }
			}

		this.material.map.needsUpdate = true;
		engine.render();
		}

	DynamicTexture.prototype.imageLoaded = function(e)
	    {
	    var img = e.target;
		var c = this.canvas.getContext( "2d" );

	    console.log(e);
        c.drawImage( img, img.x0, img.y0, img.x1-img.x0, img.y1-img.y0 );

        this.material.needsUpdate = true;
        this.material.map.needsUpdate = true;
        engine.render();
	    }


	function Engine()
		{
		this.objects = {};
		this.collision_objects = [];
		this.cameras = {}
		this.probes = {};
		this.dynamicTextures = {};

		this.scene = undefined;
		this.camera = undefined;
		this.cameraControls = undefined;
		this.renderer = undefined;
		this.composer = undefined;

        this.flags =
            {
            "antialias" : true,
            "outline" : false,
            "transparent" : false,
            "lens_distortion": false
            };

		this.phoneGeometry = undefined;

		// create materials
		this.materials = {}
		//this.materials["sphere"] = new THREE.MeshPhongMaterial( { color: 0xffffff, emissive: 0xff00ff, opacity: 0.8, transparent: true } );

		//
		// raycaster can be used for force sensor simulation
		//
		this.raycaster = new THREE.Raycaster();


		this.mouse = new THREE.Vector2();
		//document.addEventListener( 'mousemove', this.onDocumentMouseMove.bind(this), false );
		document.onmousemove = this.onDocumentMouseMove.bind(this)

		this.createScene();
		this.render();
		}

	Engine.prototype.onDocumentMouseMove = function( event )
		{
		event.preventDefault();
		this.mouse.x = ( event.clientX / window.innerWidth ) * 2 - 1;
		this.mouse.y = - ( event.clientY / window.innerHeight ) * 2 + 1;
		this.render();
		}

	Engine.prototype.addObject = function( name, parent )
		{
		console.log( "engine.addObject", name, parent );
		//
		// Creates empty object to object tree
		//
		var object = new THREE.Object3D();
		parent.add( object );
	    object.matrixAutoUpdate = false;

		object.name = name;
        this.objects[ name ] = object;


        //
        // Add coordinate frame arrows to the object:
        // notice: breaks dynamic textures at the moment
        //
        if( __MODEL_DEBUG__ )
            {
            var h = new THREE.ArrowHelper( new THREE.Vector3(1,0,0), new THREE.Vector3(0,0,0), 20, 0xff0000, 5, 2 );
            object.add( h );
            h = new THREE.ArrowHelper( new THREE.Vector3(0,1,0), new THREE.Vector3(0,0,0), 20, 0x00ff00, 5, 2 );
            object.add( h );
            h = new THREE.ArrowHelper( new THREE.Vector3(0,0,1), new THREE.Vector3(0,0,0), 20, 0x0000ff, 5, 2 );
            object.add( h );
            }

		return object;
		}

	Engine.prototype.removeObject = function( name )
	    {
	    var o = this.objects[ name ];
	    if( o )
	        {
	        freeObjectRecursive( o )
	        }
	    this.objects[ name ] = null;
	    }

	Engine.prototype.addBoxGeometry = function( parent, dim, color, tex )
	    {
	    var geometry = new THREE.BoxGeometry( dim[0], dim[1], dim[2] );
	    var material = null;

	    if( color )
	    	{
	    	material = new THREE.MeshBasicMaterial( { color: color } );
	    	}
	    else if( tex )
	    	{
	    	material = new THREE.MeshBasicMaterial( { map: tex } );
	    	}
	    else
	    	{
	    	console.log( "no color or texture!" );
	    	}

	    var object = new THREE.Mesh( geometry, material );
	    object.matrixAutoUpdate = false;

        parent.add( object );
        return object;
	    }

	Engine.prototype.addSphereGeometry = function( parent, radius, color )
	    {
	    var geometry = new THREE.SphereGeometry( radius, 20, 10 );

	    var material = new THREE.MeshBasicMaterial( { color: color } );
	    var object = new THREE.Mesh( geometry, material );
	    object.matrixAutoUpdate = false;

        parent.add( object );
        return object;
	    }

	Engine.prototype.addCylinderGeometry = function( parent, radius, height, color )
	    {
	    var geometry = new THREE.CylinderGeometry( radius, radius, height, 20, 1 );

	    var material = new THREE.MeshBasicMaterial( { color: color } );
	    var object = new THREE.Mesh( geometry, material );
	    //object.matrixAutoUpdate = false;
	    object.rotation.x = Math.PI /2;

        parent.add( object );
        return object;
	    }

	Engine.prototype.addLineGeometry = function( parent, p0, p1, color )
	    {
	    var geometry = new THREE.Geometry();
	    geometry.vertices.push( new THREE.Vector3( p0[ 0 ], p0[ 1 ], p0[ 2 ] ) );
	    geometry.vertices.push( new THREE.Vector3( p1[ 0 ], p1[ 1 ], p1[ 2 ] ) );

        var material = new THREE.MeshBasicMaterial( { color: color } );
	    var object = new THREE.Line( geometry, material );

        parent.add( object );
        return object;
	    }

	Engine.prototype.addArrowGeometry = function( parent, offset, color )
	    {
	    var l = Math.sqrt( offset[0] * offset[0] + offset[1] * offset[1] + offset[2] * offset[2] );
	    var dir = [offset[0] / l, offset[1] / l, offset[2] / l]
	    var a = new THREE.ArrowHelper( new THREE.Vector3(-dir[0],-dir[2],-dir[1]), new THREE.Vector3(0,0,0), l, color, 15, 10 );
        parent.add( a );
        return a;
	    }

    Engine.prototype.addStlGeometry = function( file, parent, color, offset=null )
		{
		console.log( "Engine.addStlGeometry", file, parent, color, offset );
		if( ! offset )
		    {
		    offset = [0, 0, 0, 0, 0, 0];
		    }
		while( offset.length < 6 )
			{
			offset.push( 0 );
			}
		var loader = new THREE.STLLoader();
		loader.load( file, this.stlLoaded.bind( this, parent, color, offset) );
		}

	Engine.prototype.stlLoaded = function( parent, color, offset, geometry )
		{
		console.log( "Engine.stlLoaded", parent, color, offset );

        // transparency is helpful when positioning STL objects
        var material;
        if( __MODEL_DEBUG__ )
            {
            material = new THREE.MeshPhongMaterial( { color: 0xffffff, emissive: color, opacity: 0.5, transparent: true } );
            }
        else
            {
            material = new THREE.MeshPhongMaterial( { color: 0xffffff, emissive: color, opacity: 1, transparent: false } );
            /*
            var alpha = 0.5;
            var beta = 0.5;
            var specularShininess = Math.pow( 2, alpha * 10 );
            material = new THREE.MeshToonMaterial( {
								color: color,
								specular: 0xffffff,
								reflectivity: beta,
								shininess: specularShininess,
								envMap: null
							} );
		    */

            }
	    var object = new THREE.Mesh( geometry, material );

		//object.matrix.set(1,0,0,offset[0], 0,1,0,offset[1], 0,0,1,offset[2], 0,0,0,1)
		//object.matrixAutoUpdate = false;
		object.position.x = offset[0];
		object.position.y = offset[1];
		object.position.z = offset[2];
		object.rotation.x = offset[3] / 180 * Math.PI;
		object.rotation.y = offset[4] / 180 * Math.PI;
		object.rotation.z = offset[5] / 180 * Math.PI;


		parent.add( object );
		this.render();

		// a little hack for testing
		//if( parent.name == 'dut' || parent.name == 'oy' )
		if( parent.name == 'dut' )
			{
			this.collision_objects.push( object );
			}
		}

	Engine.prototype.addMeshGeometry = function( parent, xa, ya, za, ua, va )
		{
		var numTriangles = xa.length / 3;

		var geometry = new THREE.BufferGeometry();
		var positions = new Float32Array( numTriangles * 3 * 3 ); // xyz * 3 points in triangle
		var normals = new Float32Array( numTriangles * 3 * 3 );   // xyz * 3 points in triangle
		var uvs = new Float32Array( numTriangles * 2 * 3 )        //  uv * 3 points in triangle
		var pA = new THREE.Vector3();
		var pB = new THREE.Vector3();
		var pC = new THREE.Vector3();
		var cb = new THREE.Vector3();
		var ab = new THREE.Vector3();

		var i = 0;
		var j = 0;
		var k = 0;
		for( var n=0; n<numTriangles; n++ )
			{
			ax = xa[ n*3 ];
			ay = ya[ n*3 ];
			az = za[ n*3 ];

			bx = xa[ n*3 + 1 ];
			by = ya[ n*3 + 1 ];
			bz = za[ n*3 + 1 ];

			cx = xa[ n*3 + 2 ];
			cy = ya[ n*3 + 2 ];
			cz = za[ n*3 + 2 ];

			positions[ i++ ] = ax;
			positions[ i++ ] = ay;
			positions[ i++ ] = az;
			positions[ i++ ] = bx;
			positions[ i++ ] = by;
			positions[ i++ ] = bz;
			positions[ i++ ] = cx;
			positions[ i++ ] = cy;
			positions[ i++ ] = cz;

			// flat face normals
			pA.set( ax, ay, az );
			pB.set( bx, by, bz );
			pC.set( cx, cy, cz );
			cb.subVectors( pC, pB );
			ab.subVectors( pA, pB );
			cb.cross( ab );
			cb.normalize();
			var nx = cb.x;
			var ny = cb.y;
			var nz = cb.z;
			normals[ j++ ]     = nx;
			normals[ j++ ] = ny;
			normals[ j++ ] = nz;
			normals[ j++ ] = nx;
			normals[ j++ ] = ny;
			normals[ j++ ] = nz;
			normals[ j++ ] = nx;
			normals[ j++ ] = ny;
			normals[ j++ ] = nz;

			uvs[ k++ ] = ua[ n*3 ];
			uvs[ k++ ] = va[ n*3 ];
			uvs[ k++ ] = ua[ n*3 + 1];
			uvs[ k++ ] = va[ n*3 + 1];
			uvs[ k++ ] = ua[ n*3 + 2];
			uvs[ k++ ] = va[ n*3 + 2];
			}

		geometry.addAttribute( 'position', new THREE.BufferAttribute( positions, 3 ) );
		geometry.addAttribute( 'normal', new THREE.BufferAttribute( normals, 3 ) );
		geometry.addAttribute( 'uv', new THREE.BufferAttribute( uvs, 2 ) );
		geometry.computeBoundingSphere();

		var material = new THREE.MeshBasicMaterial();
		var mesh = new THREE.Mesh( geometry, material );
		parent.add( mesh );

/*
				var canvas = document.createElement("canvas");

				var texture = new THREE.Texture(canvas);
				mesh.material.map = texture;
				mesh.material.map.needsUpdate = true;
*/
				mesh.material.side = THREE.DoubleSide;
				//document.body.appendChild(canvas);

		this.render();
		}

	Engine.prototype.addCamera = function( name, parent, fov, focalLength )
		{
		//
		// Add camera to object tree
		// Photos can be taken by given this name to photo function
		//
		// default fov has been 45

		if( fov === undefined ) fov = 45;

		var camera = this.cameras[ name ];
		if( ! camera )
		    {
	   	    camera = new THREE.PerspectiveCamera( fov, 4/3, 10, 8000 );
            this.cameras[ name ] = camera;
	   	    }

        parent.add( camera );
	   	if( focalLength )
	   		{
	   		camera.setLens( focalLength );
	   		}

	   	// add renderer for the camera
	   	// used when photo is taken
		var renderer = new THREE.WebGLRenderer( { antialias: true, preserveDrawingBuffer: true } );
		renderer.setClearColor( 0x223344 );
		renderer.setPixelRatio( 1 );

		// TODO: adjustable resolution
		renderer.setSize( 1920, 1440 );
		renderer.sortObjects = false;
		camera.renderer = renderer;
		camera.composer = null;

		//
		// Lens distortion
		//
		if( true )
            {
            composer = new THREE.EffectComposer( renderer );
            composer.addPass( new THREE.RenderPass( this.scene, camera ) );

            // Add distortion effect to effect composer
            var effect = new THREE.ShaderPass( getDistortionShaderDefinition() );
            composer.addPass( effect );
            effect.renderToScreen = true;

            // Setup distortion effect
            var horizontalFOV = 35;
            var strength = 1.3;
            var cylindricalRatio = 1;
            var height = Math.tan(THREE.Math.degToRad(horizontalFOV) / 2) / camera.aspect;

            camera.fov = Math.atan(height) * 2 * 180 / 3.1415926535;
            camera.updateProjectionMatrix();

            effect.uniforms[ "strength" ].value = strength;
            effect.uniforms[ "height" ].value = height;
            effect.uniforms[ "aspectRatio" ].value = this.camera.aspect;
            effect.uniforms[ "cylindricalRatio" ].value = cylindricalRatio;
            camera.composer = composer;
            }
		}

	Engine.prototype.setObjectFrame = function( name, frame )
	    {
	    // console.log("Engine.setObjectFrame", name, frame );
	    var object = this.objects[ name ];
	    object.matrixAutoUpdate = false;
	    object.matrix.set( frame[0], frame[1], frame[2], frame[3],
                           frame[4], frame[5], frame[6], frame[7],
                           frame[8], frame[9], frame[10], frame[11],
                           frame[12], frame[13], frame[14], frame[15] );

	    }

	Engine.prototype.setObjectXyzAbc = function( name, x, y, z, a, b, c )
		{
		var object = this.objects[ name ];
		object.position.x = x;
		object.position.y = y;
		object.position.z = z;
		object.rotation.x = a;
		object.rotation.y = b;
		object.rotation.z = c;
		object.matrixAutoUpdate = true;
		}

	Engine.prototype.setObjectParent = function( name, parent_name )
	    {
	    var object = this.objects[ name ];
	    var parent = this.objects[ parent_name ];
	    object.parent.remove( object );
	    parent.add( object );
	    }

	Engine.prototype.reparent = function( name, new_parent_name )
	    {
	    var object = this.objects[ name ];
	    var new_parent = this.objects[ new_parent_name ];

	    var mat = object.matrixWorld.clone()

	    object.parent.remove( object );
	    new_parent.add( object );

	    var inv = new THREE.Matrix4();
	    inv.getInverse(new_parent.matrixWorld);
        mat.multiplyMatrices(inv, mat);

	    object.matrix.copy(mat);
	    object.matrixAutoUpdate = false;
	    }

	Engine.prototype.setObjectTexture = function( object, dynamictexture )
		{
		var mesh = object.children[ 0 ];
		var texture = dynamictexture.texture;
		var material = new THREE.MeshBasicMaterial( { map: texture } );
		material.side = THREE.DoubleSide;
		mesh.material = material;
		mesh.material.map.needsUpdate = true;
		}


	/*
    Engine.prototype.framesFromJoints = function( joints )
        {
        //
        // Calculate trasform matrices for moving object from joint values
        // Override for each robot type, default is Staff 5-axis
        //
        var x = joints[ 0 ];
        var y = joints[ 1 ];
        var z = joints[ 2 ];
        var a = -joints[ 3 ] / 180 * Math.PI
        var b = joints[ 4 ] / 180 * Math.PI

        var mx = [ 1,0,0,x, 0,1,0,0, 0,0,1,0, 0,0,0,1 ];
        var my = [ 1,0,0,0, 0,1,0,y, 0,0,1,0, 0,0,0,1 ];
        var mz = [ 1,0,0,0, 0,1,0,0, 0,0,1,z, 0,0,0,1 ];

		// tilt around y-axis
        var c = Math.cos( b );
        var s = Math.sin( b );
        var mb = [ c,0,-s,0, 0,1,0,0, s,0,c,0, 0,0,0,1 ];

		// azimuth around z-axis
        c = Math.cos( a );
        s = Math.sin( a );
        var ma = [ c,-s,0,0, s,c,0,0, 0,0,1,0, 0,0,0,1 ];

		return { "ox":mx, "oy":my, "oz": mz, "oa": ma, "ob": mb }
        }
	*/
    Engine.prototype.moveObjectsWithJoints = function( joints )
        {
        //
        // Moves visible objects with joint values
        //

        // all axis must be included
        var f = simulator.frame;
        for( var a in f ){ if( ! (a in joints)) {joints[a] = f[a];}}

        var frames = this.framesFromJoints( joints );
        for( var name in frames )
        	{
        	var m = frames[ name ];
        	if( m != undefined )
        		{
        		this.setObjectFrame( name, m );
        		}
        	}
        }


	Engine.prototype.createScene = function()
		{
		this.scene = new THREE.Scene();

		//
		// Default simulator camera, used to visualize on the webpage
		//
		this.camera = new THREE.PerspectiveCamera( 55, 4/3, 10, 18000 );


		//
		// simulation view renderer
		//
		//this.renderer = new THREE.WebGLRenderer();
		this.renderer = new THREE.WebGLRenderer( { antialias: this.flags['antialias'] } );
		this.renderer.setClearColor( 0x223344 );
		//this.renderer.setPixelRatio( window.devicePixelRatio );
		this.renderer.setPixelRatio( 1 );

		this.w = 1280;
		this.h = 960;
		this.renderer.setSize( this.w, this.h );
		this.renderer.sortObjects = false;

        //this.outlineEffect = new THREE.OutlineEffect( this.renderer );

		//
		// Lens distortion
		//
        composer = new THREE.EffectComposer( this.renderer );
        composer.addPass( new THREE.RenderPass( this.scene, this.camera ) );

        // Add distortion effect to effect composer
        var effect = new THREE.ShaderPass( getDistortionShaderDefinition() );
        composer.addPass( effect );
        effect.renderToScreen = true;

        // Setup distortion effect
        var horizontalFOV = 45;
        var strength = 1.5;
        var cylindricalRatio = 2;
        var height = Math.tan(THREE.Math.degToRad(horizontalFOV) / 2) / this.camera.aspect;

        this.camera.fov = Math.atan(height) * 2 * 180 / 3.1415926535;
        this.camera.updateProjectionMatrix();

        effect.uniforms[ "strength" ].value = strength;
        effect.uniforms[ "height" ].value = height;
        effect.uniforms[ "aspectRatio" ].value = this.camera.aspect;
        effect.uniforms[ "cylindricalRatio" ].value = cylindricalRatio;
        this.lensEffect = effect;
        this.lensComposer = composer;

        //
        //
        //

        var base = document.getElementById( "canvas_base" );
		base.appendChild( this.renderer.domElement );

		// lights
		var mainLight = new THREE.PointLight( 0xffffff, 1.5, 3500, 0.7 );
		mainLight.position.set( 200, 1500, 2500 );
		this.scene.add( mainLight );

		// camera options
		this.camera.position.z = 1000;
		this.camera.position.y = 1000;

		cameraControls = new THREE.OrbitControls( this.camera, this.renderer.domElement );
		cameraControls.target.set( 0, 0, 0 );
		cameraControls.addEventListener( 'change', this.render.bind(this) );
		this.cameraControls = cameraControls;

		// root object
		var root = this.addObject( "root", this.scene );
		this.setObjectXyzAbc( "root", 0, 0, 0, 3.14/2, 0, 0 );

		// update renderer with window resize
		window.onresize = function()
		    {
		    engine.render();
		    }
		}


	var framecounter = 0;

	Engine.prototype.render = function()
		{
		requestAnimationFrame( this.render2.bind(this) );
        }

    Engine.prototype.render2 = function()
        {
		var b = this.renderer.domElement.parentElement;
		var w = b.clientWidth;
		var h = b.clientHeight;

        var screenchanged = false;
		if( w != this.w || h != this.h )
		    {
		    this.w = w;
		    this.h = h;
            this.camera.aspect = w / h;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize( w, h );
            screenchanged = true;
            }

        this.renderer.antialias = this.flags["antialias"];

        if( this.flags["outline"] )
            {
            this.outlineEffect.render( this.scene, this.camera );
            }
        else if( this.flags["lens_distortion"] )
            {
            this.lensComposer.render();

            if( screenchanged )
                {
                // Setup distortion effect
                var horizontalFOV = 45;
                var strength = 1.5;
                var cylindricalRatio = 2;
                var height = Math.tan(THREE.Math.degToRad(horizontalFOV) / 2) / this.camera.aspect;

                this.camera.fov = Math.atan(height) * 2 * 180 / 3.1415926535;
                this.camera.updateProjectionMatrix();

                effect = this.lensEffect;
                effect.uniforms[ "strength" ].value = strength;
                effect.uniforms[ "height" ].value = height;
                effect.uniforms[ "aspectRatio" ].value = this.camera.aspect;
                effect.uniforms[ "cylindricalRatio" ].value = cylindricalRatio;
                }
            }
        else
            {
            this.renderer.render( this.scene, this.camera );
            }

		}


	Engine.prototype.addProbe = function( name, parent_name )
		{
		var probe = new Probe( name, parent_name );
		this.probes[ name ] = probe;
		return probe;
		}


	//
	//
	//

    function Simulator()
        {
        this.frames = [];
        this.frame = {};
        this.running = false;
        this.grams = 0;
        }

    Simulator.prototype.addFrames = function( frames )
        {
        this.frames.push.apply( this.frames, frames );

        if( ! this.running )
            {
            this.tick();
            }
        }

    Simulator.prototype.update_frame = function(f)
        {
        for( var n in f ){this.frame[n] = f[n]}
        }

    Simulator.prototype.tick = function()
        {
        if( this.frames.length == 0 ) return;

        var f = this.frames[ 0 ];
        this.frames.splice( 0, 1 );
        engine.moveObjectsWithJoints( f );
        this.update_frame( f );

        engine.render();

        if( this.frames.length > 0 )
            {
            this.running = true;
            setTimeout( this.tick.bind( this ), 1000/FPS );
            }
        else
            {
            this.running = false;
            }
        }

	//
	//
	//

	function listObjectsRecursive( o, list )
		{
		if( ! list ) list = [];
		list.push( o );
		for( var i=0; i<o.children.length; i++ )
			{
			var child = o.children[ i ];
			listObjectsRecursive( child, list );
			}
		return list;
		}

	function freeObjectRecursive( o )
		{
		var objects = listObjectsRecursive( o );
		for( var i=0; i<objects.length; i++ )
			{
			var o = objects[ i ];

            if( o.parent ) o.parent.remove( o );

			var object = objects[ i ];
			try
				{
				o.material.dispose();
				console.log( "successfully freed material" );
				}
			catch( err )
				{
				//console.log( err );
				}
			try
				{
				o.geometry.dispose();
				console.log( "successfully freed geometry" );
				}
			catch( err )
				{
				//console.log( err );
				}
			try
				{
				o.dispose();
				console.log( "successfully freed object" );
				}
			catch( err )
				{
				//console.log( err );
				}
			}
		}


    function handleCmd( cmd, s )
        {
        //
        // Handle newline separated commands
        //

        //console.log( "handleCmd", cmd );
        if( cmd == "" ) return;

        var params = [];
        var p = cmd.indexOf(' ');
        if( p >= 0 )
            {
            params = cmd.substr(p+1) //.split(',');
            cmd = cmd.substr(0, p);
            }
        cmd = cmd.toLowerCase()
        //console.log( "Command : " + cmd );
        //console.log( "Params  : " + params );

        try
            {
            if( cmd == 'mov' )
                {
                try
                    {
                    var data = JSON.parse( params );

                    var data_len = check_data_len(data);

                    frames = [];
                    var stp = Math.round(250/FPS); // trajectory points at 250 Hz
                    var i = 0;
                    var n = data_len;
                    while( true )
                        {
                        var frame = {};
                        for (var key in data)
                            {
                            frame[key] = data[key][i];
                            }
                        frames.push(frame);

                        if( i == n-1 ) break;
                        i += stp;
                        if( i >= n ) i = n-1;
                        }
                    simulator.addFrames( frames );
                    }
                catch( err )
                    {
                    console.log("ignoring error", err );
                    }
                rv = 'ok';
                }

            else if( cmd == 'abs' )
                {
                try
                    {
                    var data = JSON.parse( params );

                    var data_len = check_data_len(data);

                    simulator.addFrames([data]);
                    }
                catch( err )
                    {
                    console.log("ignoring error", err );
                    }
                rv = 'ok';
                }
            else if( cmd == 'photo' )
            	{
            	params = JSON.parse( params );

            	var cameraName = params["name"];
            	var camera = engine.cameras[ cameraName ];
            	var renderer = camera.renderer;
            	var composer = camera.composer;
    			if( composer )
    			    {
    			    // if there is effect composer like lens distrortion
    			    composer.render();
    			    }
                else
                    {
    				renderer.render( engine.scene, camera )
    				}

				var strMime = "image/jpeg";

				var imgData = renderer.domElement.toDataURL(strMime);
				rv = imgData;
				rv += "\nok";
            	}

            else if( cmd == 'pos' )
                {
                var j = simulator.frame;
                rv = JSON.stringify(j);
                rv += "\nok"
                }

            else if( cmd == 'busy' )
                {
                var busy = simulator.running;
                rv = JSON.stringify( busy );
                rv += "\nok"
                }

            else if( cmd == 'reset_model' )
            	{
            	var root_object = engine.objects[ 'root' ];
            	while( root_object.children.length )
            		{
            		var child = root_object.children[ 0 ];
            		freeObjectRecursive( child );
            		}
            	engine.objects = { "root" : root_object };
				engine.collision_objects = [];
				engine.probes = {};

            	rv = 'ok';
            	}

            else if( cmd == 'add_object' )
            	{
            	params = JSON.parse( params );

				var name = params[ "name" ]
				var parent_name = params[ "parent_name" ];

				var parent_object = engine.objects[ parent_name ];

				// create node object, connect to parent object
				engine.addObject( name, parent_object );
				rv = 'ok';
				}

            else if( cmd == 'remove_object' )
            	{
            	params = JSON.parse( params );

				var name = params[ "name" ]
				// remove object and free all resources including textures
				engine.removeObject( name );
				engine.render()
				rv = 'ok';
				}

            else if( cmd == 'move_object' )
            	{
            	params = JSON.parse( params );

				var name = params[ "name" ]
				var c = params[ "coordinates" ];
				var p = params[ "parent" ];

				engine.setObjectXyzAbc( name, c[0], c[1], c[2], c[3], c[4], c[5] );

				if( p )
				    {
				    engine.setObjectParent( name, p );
				    }

				engine.render();

				rv = 'ok';
				}

			else if( cmd == 'set_object_frame' )
            	{
            	params = JSON.parse( params );

				var name = params[ "name" ];
				var frame = params[ "frame" ];

                engine.setObjectFrame( name, [1,0,0,0, 0,1,0,0, 0,0,-1,0, 0,0,0,1])
				engine.render();

				rv = 'ok';
				}

			else if( cmd == 'reparent')
			    {
			        params = JSON.parse( params );

                    var name = params[ "name" ]
                    var p = params[ "new_parent" ];

                    if( p )
				    {
				    engine.reparent( name, p );
				    }


				    rv = 'ok';
			    }

            else if( cmd == 'add_stl' )
            	{
            	params = JSON.parse( params );

				var url = params[ "url" ];
				var parent_name = params[ "parent_name" ]
				var color = params[ "color" ]
				var offset = params[ "offset" ]

            	console.log( "add_stl", url, parent_name, color, offset );

				parent_object = engine.objects[ parent_name ];

				// start loading 3d-model from file, will be connected to node object when loaded
				engine.addStlGeometry( url, parent_object, color, offset );

				rv = 'ok';
            	}

            else if( cmd == 'add_box' )
            	{
            	params = JSON.parse( params );

				var parent_name = params[ "parent_name" ];
				var color = params[ "color" ];
				var size = params[ "size" ];
				var texture = params[ "texture" ];

				// size can be one number or x,y,z dimensions
				if( ! size.constructor === Array )
					{
					size = [ size, size, size ];
					}

				console.log("Add_box", parent_name, color, size, texture);

				parent_object = engine.objects[ parent_name ];
				if( color )
					{
					engine.addBoxGeometry( parent_object, size, color, null);
					}
				else if( texture )
					{
					console.log(texture)
					var tex = new THREE.TextureLoader().load( texture );
					engine.addBoxGeometry( parent_object, size, null, tex);
					}
				else
					{
					console.log("No color or texture!")
					}
				rv = 'ok';
            	}

            else if( cmd == 'add_sphere' )
            	{
            	params = JSON.parse( params );

				var parent_name = params[ "parent_name" ]
				var color = params[ "color" ]
				var radius = params[ "radius" ]

				parent_object = engine.objects[ parent_name ];
				engine.addSphereGeometry( parent_object, radius, color, null );
				rv = 'ok';
            	}

            else if( cmd == 'add_cylinder' )
            	{
            	params = JSON.parse( params );

				var parent_name = params[ "parent_name" ]
				var color = params[ "color" ]
				var radius = params[ "radius" ]
				var height = params[ "height" ]

				parent_object = engine.objects[ parent_name ];
				engine.addCylinderGeometry( parent_object, radius, height, color );
				rv = 'ok';
            	}

            else if( cmd == 'add_line' )
                {
                params = JSON.parse( params );

                var parent_name = params[ "parent_name" ];
                var color = params[ "color" ];
                var p0 = params[ "p0" ];
                var p1 = params[ "p1" ];
                parent_object = engine.objects[ parent_name ];
                engine.addLineGeometry( parent_object, p0, p1, color );
                rv = 'ok';
                }

            else if( cmd == 'add_mesh' )
            	{
            	params = JSON.parse( params );
            	var x_list = params['x'];
            	var y_list = params['y'];
            	var z_list = params['z'];
            	var u_list = params['u'];
            	var v_list = params['v'];

            	// lists must have same length
            	// where xyz are xyz position of vertex
            	// and uv are 0..1 texture coordinates of vertex
            	// list length must be dividable by 3
            	// because 3 vertices per triangle

            	var parent_name = params[ "parent_name" ]
            	parent_object = engine.objects[ parent_name ];
            	engine.addMeshGeometry( parent_object, x_list, y_list, z_list, u_list, v_list );
				rv = 'ok';
            	}

            else if( cmd == 'set_object_texture' )
            	{
            	params = JSON.parse( params );

				var object = engine.objects[ params[ "object_name" ] ];
				var texture = engine.dynamicTextures[ params[ "texture_name" ] ];
				engine.setObjectTexture( object, texture );
            	}

            else if( cmd == 'create_dynamic_texture' )
            	{
            	params = JSON.parse( params );

				var name = params[ "name" ]
				var width = params[ "width" ]
				var height = params[ "height" ]

				engine.dynamicTextures[ name ] = new DynamicTexture( width, height );
				}

			else if( cmd == 'draw_dynamic_texture' )
				{
				params = JSON.parse( params );

				var name = params[ "name" ];
				var program = params[ "program" ];
				var scale = params[ "scale" ];
				if( ! scale ) scale = 1.0;

				var dynamicTexture = engine.dynamicTextures[ name ];
				dynamicTexture.draw( program, scale );
				}

            else if( cmd == 'set_kinematic_function' )
            	{
            	params = JSON.parse( params );
            	var f_str = params["f"];
            	f_str = "engine.framesFromJoints=" + f_str;
            	var f = eval( f_str );

            	rv = 'ok';
            	}

            else if( cmd == 'set_axes' )
            	{
            	var params = JSON.parse( params );
            	var f = {}
            	for( var deviceaddress in params )
            	    {
            	    var ax = params[deviceaddress];
            	    var alias = ax['alias']
            	    f[ alias ] = 0.0;
            	    }
            	simulator.addFrames([f]);

            	rv = 'ok';
            	}


            else if( cmd == 'add_camera' )
            	{
            	params = JSON.parse( params );

            	var name = params[ "name" ];
            	var parent_name = params[ "parent_name" ];
            	var fov = params[ "fov" ];
            	var focalLength = params[ "focal_length" ];
            	var parent = engine.objects[ parent_name ];
            	engine.addCamera( name, parent, fov, focalLength );
            	rv = 'ok';
            	}

            else if( cmd == 'add_probe' )
            	{
            	params = JSON.parse( params );

            	var name = params[ "name" ];
            	var parent_name = params[ "parent_name" ];
            	engine.addProbe( name, parent_name );
            	rv = 'ok';
            	}

            else if( cmd == 'read_probe' )
            	{
            	params = JSON.parse( params );

            	var name = params[ "name" ];
            	var probe = engine.probes[ name ];
            	var distance = probe.read();
            	rv = JSON.stringify( distance );
            	rv += '\nok';
            	}

            else if( cmd == 'set_title' )
                {
                var title = params;
                document.getElementById( 'title_div' ).innerHTML = title;
                rv = 'ok';
                }

            else if( cmd == 'force' )
                {
                params = JSON.parse( params );
                this.grams = 0 + params["grams"];
                rv = 'ok';
                }

            else if( cmd == 'get_force' )
                {
                params = JSON.parse( params );
                rv = '' + this.grams + '\nok'
                }

            else if( cmd == 'create_sensor' )
            	{
            	rv = 'ok';
            	}
            else if( cmd == 'set_camera_up')
                {
                    params = JSON.parse( params );
                    var up_x = params['up_x'];
                    var up_y = params['up_y'];
                    var up_z = params['up_z'];
                    engine.camera.up.set(up_x, up_y, up_z)

                    engine.cameraControls.reset()
                    engine.render()
                }

            else
                {
                rv = 'error';
                }
            }
        catch( err )
            {
            simulator.running = false;
            console.log( err );
            rv = 'error:' + err;
            }
        //console.log( "Sending back:" + rv );
        return rv;
        }

    function malert(s)
        {
        console.log("malert",s);
        return;
        }

    function initCommunication()
        {

        var s = new WebSocket("ws://localhost:9876/");
        s.onopen = function(e)
            {
            malert("opened");
            s.send("opened")
            this.buffer = "";

            }
        s.onclose = function(e) { malert("closed"); }
        s.onmessage = function(e)
            {
            //console.log("got: ", e.data);
            this.buffer += e.data;

            // messages split with newline

            var p = this.buffer.search("\n");
            if( p < 0 )
                {
                return;
                }
            var msg = this.buffer.substr( 0, p );
            this.buffer = this.buffer.substr( p+1 );

            var cmds = msg.trim().split('\n');
            var rv = "";
            for( var i=0; i<cmds.length; i++ )
                {
                var cmd = cmds[ i ];
                rv += handleCmd( cmd, s );
                rv += '\n';
                }

            s.send(rv)
            }

        };

function check_data_len(data)
    {
    var data_len = 0;
    for (var key in data)
        {
        var l = data[key].length;

        if( l != 0 )
            {
            return l;
            }
        }
    return data_len;
    }
