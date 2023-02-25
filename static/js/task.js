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
const componentLabels = [majorClaim, claimFor, claimAgainst, premise]

const support = 'S'
const attack = 'A'
const relationLabels = [support, attack]

function getLabels(ann) {
  return ann.body.filter(b => b.purpose === 'tagging').map(b => b.value);
}

function getComponents(recogito) {
    return recogito.getAnnotations().filter(ann => ann.motivation !== 'linking')
}

function formatAnn(ann) {
  const label = getLabels(ann)[0]

  let highlightClass = '';
  if (label === majorClaim) {
    highlightClass = 'major-claim';
  } else if (label === claimFor) {
      highlightClass = 'claim-for';
  } else if (label === claimAgainst) {
      highlightClass = 'claim-against';
  } else if (label === premise) {
      highlightClass = 'premise';
  }

  return highlightClass
}

function checkComponentLabel(ann, recogito) {
  const labels = getLabels(ann)

  if (labels.length === 0) {
      window.alert(`Tag must be selected for the highlighted text area.`)
      recogito.removeAnnotation(ann)
  } else if (labels.length > 1) {
      window.alert(`Only one tag is allowed per highlighted text area.`)
      recogito.removeAnnotation(ann)
  } else if (!componentLabels.includes(labels[0])) {
      window.alert(`Tag '${labels[0]}' is invalid, please add one the following: ${componentLabels.join(', ')}.`)
      recogito.removeAnnotation(ann)
  }

}

function checkComponentSpan(ann, recogito) {
  const annId = ann.id;
  const annPosSelector = ann.target.selector.find(s => s.type === 'TextPositionSelector');
  const annStart = annPosSelector.start;
  const annEnd = annPosSelector.end;

  const others = getComponents(recogito);
  const overlapping = others.filter(other => {
    let result = false;

    if (annId !== other.id) {
      const otherPosSelector = other.target.selector.find(s => s.type === 'TextPositionSelector');
      const otherStart = otherPosSelector.start;
      const otherEnd = otherPosSelector.end;
      const noOverlap = otherEnd < annStart || otherStart > annEnd;
      result = !noOverlap;
    }

    return result;
  });

  if (overlapping.length > 0) {
    window.alert('Highlighted text areas must not overlap.')
    recogito.removeAnnotation(ann)
  }
}

function initRecogito() {
  // Intialize Recogito
  const recogito = Recogito.init({
    content: 'content', // Element id or DOM node to attach to
    locale: 'auto',
    allowEmpty: true,
    widgets: [
      { widget: 'TAG', vocabulary: [ 'MajorClaim', 'ClaimFor', 'ClaimAgainst', 'Premise' ] }
    ],
    relationVocabulary: [ 'Support', 'Attack' ],
    formatter: formatAnn
  });

  recogito.on('selectAnnotation', function(a) {
    console.log('selected', a);
  });

  recogito.on('createAnnotation', function(ann) {
    // TODO: need to tune recogito to be able to access relations
    // if (a.motivation === 'linking') {
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
      //  console.log(recogito)
    // }
    // console.log('created')

    if (ann.motivation !== 'linking') {
      checkComponentLabel(ann, recogito)
      checkComponentSpan(ann, recogito)
    }
  });

  recogito.on('updateAnnotation', function(annotation, previous) {
    console.log('updated', previous, 'with', annotation);
  });

  recogito.on('cancelSelected', function(annotation) {
    console.log('cancel', annotation);
  });

  document.getElementById('get-annotations').addEventListener('click', function() {
    console.log('annotations', recogito.getAnnotations());
  });

  // Switch annotation mode (annotation/relationships)
  let annotationMode = 'ANNOTATION'; // or 'RELATIONS'

  let toggleModeBtn = document.getElementById('toggle-mode');
  toggleModeBtn.addEventListener('click', function() {
    if (annotationMode === 'ANNOTATION') {
      toggleModeBtn.innerHTML = 'MODE: RELATIONS';
      annotationMode = 'RELATIONS';
    } else  {
      toggleModeBtn.innerHTML = 'MODE: ANNOTATION';
      annotationMode = 'ANNOTATION';
    }

    recogito.setMode(annotationMode);
  });
}


const StroopExperiment = function () {
  // Load the stage.html snippet into the body of the page
  psiTurk.showPage('stage.html');

  initRecogito()

  $("#submit-sam").click(function () {
      currentview = new Questionnaire();
  });
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
