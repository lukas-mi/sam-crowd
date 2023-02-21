/*
 * Requires:
 *     psiturk.js
 *     utils.js
 */

// Initalize psiturk object
var psiTurk = new PsiTurk(uniqueId, adServerLoc, mode);

var mycondition = condition;  // these two variables are passed by the psiturk server process
var mycounterbalance = counterbalance;  // they tell you which condition you have been assigned to
// they are not used in the stroop code but may be useful to you

// All pages to be loaded
var pages = [
	"instructions/instruct-1.html",
	"instructions/instruct-ready.html",
	"stage.html",
	"postquestionnaire.html"
];

// In javascript, defining a function as `async` makes it return  a `Promise`
// that will "resolve" when the function completes. Below, `init` is assigned to be the
// *returned value* of immediately executing an anonymous async function.
// This is done by wrapping the async function in parentheses, and following the
// parentheses-wrapped function with `()`.
// Therefore, the code within the arrow function (the code within the curly brackets) immediately
// begins to execute when `init is defined. In the example, the `init` function only
// calls `psiTurk.preloadPages()` -- which, as of psiTurk 3, itself returns a Promise.
//
// The anonymous function is defined using javascript "arrow function" syntax.
const init = (async () => {
    await psiTurk.preloadPages(pages);
})()

var instructionPages = [ // add as a list as many pages as you like
	"instructions/instruct-1.html",
	"instructions/instruct-ready.html"
];


/********************
* HTML manipulation
*
* All HTML files in the templates directory are requested
* from the server when the PsiTurk object is created above. We
* need code to get those pages from the PsiTurk object and
* insert them into the document.
*
********************/

/********************
* STROOP TEST       *
********************/
const majorClaim = 'MajorClaim';
const claimFor = 'ClaimFor';
const claimAgainst = 'ClaimAgainst';
const premise = 'Premise';


var StroopExperiment = function() {
    // Load the stage.html snippet into the body of the page
	psiTurk.showPage('stage.html');

    // const TestFormatter = function(annotation) {
    //     const body = annotation.bodies.find(function(b) {
    //       return b.purpose === 'tagging'
    //     });
    //
    //     let highlightClass = '';
    //     if (body !== undefined) {
    //         if (body.value === majorClaim) {
    //         highlightClass = 'major-claim';
    //       } else if (body.value === claimFor) {
    //           highlightClass = 'claim-for';
    //       } else if (body.value === claimAgainst) {
    //           highlightClass = 'claim-against';
    //       } else if (body.value === premise) {
    //           highlightClass = 'premise';
    //       }
    //     }
    //
    //     console.log('TestFormatter')
    //     console.log(annotation)
    //     // console.log(annotation.bodies)
    //     // console.log(highlightClass)
    //     return highlightClass
    // }

    (function() {
  // Intialize Recogito
  var r = Recogito.init({
        content: 'outer-container', // Element id or DOM node to attach to
        locale: 'auto',
        allowEmpty: true,
        widgets: [
          // { widget: 'COMMENT' },
          { widget: 'TAG', vocabulary: [ 'MajorClaim', 'ClaimFor', 'ClaimAgainst', 'Premise' ] }
        ],
        relationVocabulary: [ 'Support', 'Attack' ],
        // formatter: TestFormatter
      });

      r.loadAnnotations('annotations.w3c.json')
        .then(() => console.log('loaded'));

      r.on('selectAnnotation', function(a) {
        console.log('selected', a);
      });

      r.on('createAnnotation', function(a) {
        console.log('created', a);
        console.log(a.bodies);
        // TODO: need to tune recogito to be able to access relations
        if (a.motivation === 'linking') {
          // const rel = a.body[0].value
          // if (rel !== 'Support' || rel !== 'Attack') {
          //   const found = r.getAnnotations().find(function(ann) {
          //     return ann.id === a.id;
          //   });
          //   console.log('found', found);
          //   console.log('remove', r.removeAnnotation(found))
          // }
          // console.log('remove', r.removeRelation(a))
          // console.log("linking", a.id, a.body[0].value)
            console.log(r)
        }
      });

      r.on('updateAnnotation', function(annotation, previous) {
        console.log('updated', previous, 'with', annotation);
      });

      r.on('cancelSelected', function(annotation) {
        console.log('cancel', annotation);
      });

      document.getElementById('get-annotations').addEventListener('click', function() {
        console.log('annotations', r.getAnnotations());
      });

      // Switch annotation mode (annotation/relationships)
      var annotationMode = 'ANNOTATION'; // or 'RELATIONS'

      var toggleModeBtn = document.getElementById('toggle-mode');
      toggleModeBtn.addEventListener('click', function() {
        if (annotationMode === 'ANNOTATION') {
          toggleModeBtn.innerHTML = 'MODE: RELATIONS';
          annotationMode = 'RELATIONS';
        } else  {
          toggleModeBtn.innerHTML = 'MODE: ANNOTATION';
          annotationMode = 'ANNOTATION';
        }

        r.setMode(annotationMode);
      });
    })();

    $("#submit-sam").click(function() {
      console.log('changing!!!')
      currentview = new Questionnaire();
    });

    // document.getElementById('submit-sam').addEventListener('click', function() {
    //     console.log('changing!!!');
    // });
};


/****************
* Questionnaire *
****************/

var Questionnaire = function() {

	var error_message = "<h1>Oops!</h1><p>Something went wrong submitting your HIT. This might happen if you lose your internet connection. Press the button to resubmit.</p><button id='resubmit'>Resubmit</button>";

	record_responses = function() {

		psiTurk.recordTrialData({'phase':'postquestionnaire', 'status':'submit'});

		$('textarea').each( function(i, val) {
			psiTurk.recordUnstructuredData(this.id, this.value);
		});
		$('select').each( function(i, val) {
			psiTurk.recordUnstructuredData(this.id, this.value);
		});

	};

	prompt_resubmit = function() {
		document.body.innerHTML = error_message;
		$("#resubmit").click(resubmit);
	};

	resubmit = function() {
		document.body.innerHTML = "<h1>Trying to resubmit...</h1>";
		reprompt = setTimeout(prompt_resubmit, 10000);

		psiTurk.saveData({
			success: function() {
			    clearInterval(reprompt);
                psiTurk.computeBonus('compute_bonus', function(){
                	psiTurk.completeHIT(); // when finished saving compute bonus, the quit
                });


			},
			error: prompt_resubmit
		});
	};

	// Load the questionnaire snippet
	psiTurk.showPage('postquestionnaire.html');
	psiTurk.recordTrialData({'phase':'postquestionnaire', 'status':'begin'});

	$("#next").click(function () {
	    record_responses();
	    psiTurk.saveData({
            success: function(){
                psiTurk.computeBonus('compute_bonus', function() {
                	psiTurk.completeHIT(); // when finished saving compute bonus, the quit
                });
            },
            error: prompt_resubmit});
	});


};

// Task object to keep track of the current phase
var currentview;

/*******************
 * Run Task
 ******************/
 // In this example `task.js file, an anonymous async function is bound to `window.on('load')`.
 // The async function `await`s `init` before continuing with calling `psiturk.doInstructions()`.
 // This means that in `init`, you can `await` other Promise-returning code to resolve,
 // if you want it to resolve before your experiment calls `psiturk.doInstructions()`.

 // The reason that `await psiTurk.preloadPages()` is not put directly into the
 // function bound to `window.on('load')` is that this would mean that the pages
 // would not begin to preload until the window had finished loading -- an unnecessary delay.
$(window).on('load', async () => {
    await init;
    psiTurk.doInstructions(
    	instructionPages, // a list of pages you want to display in sequence
    	function() { currentview = new StroopExperiment(); } // what you want to do when you are done with instructions
    );
});
