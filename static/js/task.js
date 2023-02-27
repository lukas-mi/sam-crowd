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
          const componentLabels = [majorClaim, claimFor, claimAgainst, premise];
          const regularClaimLabels = [claimFor, claimAgainst];
          const claimLabels = [majorClaim, claimFor, claimAgainst];

          const support = 'Support';
          const attack = 'Attack';
          const relationLabels = [support, attack];

          function getLabels(ann) {
            return ann.body.filter(b => b.purpose === 'tagging').map(b => b.value);
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

          function isComponentValid(comp, recogito) {
            return isComponentLabelValid(comp) && isComponentSpanValid(comp, recogito.getAnnotationsOnly());
          }

          function isComponentLabelValid(comp) {
            const labels = getLabels(comp)

            let isValid = false
            if (labels.length === 0) {
              window.alert(`A tag must be added for the highlighted text area.`);
            } else if (labels.length > 1) {
              window.alert(`Only one tag is allowed per highlighted text area.`);
            } else if (!componentLabels.includes(labels[0])) {
              window.alert(`Tag '${labels[0]}' is invalid, please add one the following: ${componentLabels.join(', ')}.`);
            } else {
              isValid = true;
            }

            return isValid
          }

          function isComponentSpanValid(comp, others) {
            const compId = comp.id;
            const compPosSelector = comp.target.selector.find(s => s.type === 'TextPositionSelector');
            const compStart = compPosSelector.start;
            const compEnd = compPosSelector.end;

            const overlapping = others.filter(other => {
              let result = false;

              if (compId !== other.id) {
                const otherPosSelector = other.target.selector.find(s => s.type === 'TextPositionSelector');
                const otherStart = otherPosSelector.start;
                const otherEnd = otherPosSelector.end;
                const noOverlap = otherEnd < compStart || otherStart > compEnd;
                result = !noOverlap;
              }

              return result;
            });

            let isValid = true;
            if (overlapping.length > 0) {
              isValid = false;
              window.alert('Highlighted text areas must not overlap.');
            }

            return isValid
          }

          function propagateComponentUpdate(prevComp, curComp, recogito) {
            const relations = recogito.getRelationsOnly();
            const prevLabel = getLabels(prevComp)[0];
            const curLabel = getLabels(curComp)[0];

            let relationsToRemove = [];
            let errMsg = '';

            if (prevLabel === premise && regularClaimLabels.includes(curLabel)) { // premise to regular claim => remove outgoing connection
              const outRelation = relations.find(rel => rel.target[0].id === curComp.id);
              relationsToRemove = outRelation ? [outRelation] : [];
              errMsg = `Outgoing connection was removed for the component due to tag change: ${prevLabel} -> ${curLabel}.`;
            } else if (prevLabel === premise && curLabel === majorClaim) { // premise to major claim => remove all connections
              relationsToRemove = relations.filter(rel => rel.target[0].id === curComp.id || rel.target[1].id === curComp.id);
              if (relationsToRemove)
              errMsg = `All connection were removed for the component due to tag change: ${prevLabel} -> ${curLabel}.`;
            } else if (regularClaimLabels.includes(prevLabel) && prevLabel === majorClaim) { // regular claim to major claim => remove all incoming connections
              relationsToRemove = relations.filter(rel => rel.target[1].id === curComp.id);
              errMsg = `All incoming connection were removed for the component due to tag change: ${prevLabel} -> ${curLabel}.`;
            }

            relationsToRemove.forEach(rel => {
              console.log('removing relation', rel);
              recogito.removeRelation(rel);
            });
            if (relationsToRemove.length > 0) {
              alert(errMsg);
            }
          }

          function validatePremises(recogito) {
            const premises = recogito.getAnnotationsOnly().filter(p => getLabels(p)[0] === premise);
            const relations = recogito.getRelationsOnly();

            const unlinkedPremises = premises.filter(p => relations.find(r => r.target[0].id === p.id) === undefined);

            let valid = true

            $(`#errors-container`).remove();
            if (unlinkedPremises.length > 0) {
              valid = false;

              const alertDiv = $(`<div id="errors-container" class="alert alert-danger"></div>`);

              const generalMsg = $(`<h3>Cannot submit due to incomplete annotation</h3>`)
              const errP1 = $(`<p>All premise components need to be linked to another component (${premise}/${claimFor}/${claimAgainst}) and the last component in the argument chain has to be ${claimFor}/${claimAgainst}.</p>`);
              const errP2 = $(`<p>To address this you can do one of the following (please refer to the guidelines when making the decision):</p>`);
              const suggestionList = $(`<ul></ul>`);
              suggestionList.append(`<li>Link the ${premise} to ${claimFor}/${claimAgainst} component via ${support}/${attack} relation.</li>`);
              suggestionList.append(`<li>Change component's tag to ${claimFor}/${claimAgainst}.</li>`);
              suggestionList.append(`<li>Remove the component.</li>`);

              const itemsP = $(`<p>Following ${premise} components do not adhere to the rule described above:</p>`)
              const itemList = $(`<ul></ul>`);
              unlinkedPremises.forEach(p => {
                const listItem = $(`<li><span class="r6o-annotation premise">${p.target.selector[0].exact}</span></li>`);
                itemList.append(listItem);
              });

              alertDiv.append(generalMsg, errP1, errP2, suggestionList, itemsP, itemList);
              $("#outer-container").append(alertDiv);

              alert("Cannot submit due to incomplete annotation, please see reasons at the bottom of the page and address them.");
            }

            return valid;
          }

          function isRelationValid(rel, recogito) {
            const fromComp = recogito.getAnnotationById(rel.target[0].id);
            const toComp = recogito.getAnnotationById(rel.target[1].id);
            const relations = recogito.getRelationsOnly();
            return isRelationLabelValid(rel, recogito) &&
                isRelationLinkValid(fromComp, toComp) &&
                isSingleLink(rel, relations, fromComp) &&
                noCycles(rel, relations);
          }

          function isRelationLabelValid(ann) {
            const labels = getLabels(ann);

            let isValid = false;
            if (labels.length === 0) {
              window.alert(`A tag must be added to the relation.`);
            } else if (labels.length > 1) {
              window.alert(`Only one tag is allowed per relation.`);
            } else if (!relationLabels.includes(labels[0])) {
              window.alert(`Tag '${labels[0]}' is invalid, please add one the following: ${relationLabels.join(', ')}.`);
            } else {
              isValid = true;
            }

            return isValid;
          }

          function isRelationLinkValid(fromAnn, toAnn) {
            const fromLabel = fromAnn.body[0].value;
            const toLabel = toAnn.body[0].value;
            const isValid = fromLabel === premise && (toLabel === claimFor || toLabel === claimAgainst || toLabel === premise);

            if (!isValid) {
              window.alert(`Component of type ${fromLabel} cannot be linked to ${toLabel}.`);
            }

            return isValid;
          }

          function isSingleLink(rel, others, fromComp) {
            const otherLinks = others.filter(other => {
                let result = false;

                if (rel.id !== other.id) {
                  const otherFromId = other.target[0].id;
                  result = fromComp.id === otherFromId;
                }

                return result;
            });

            let isValid = true;
            if (otherLinks.length > 0) {
                isValid = false;
                const fromCompLabel = fromComp.body[0].value;
                window.alert(`Component of type ${fromCompLabel} cannot be linked to multiple other components.`);
            }

            return isValid;
          }

          function noCycles(rel, relations) {
              // const others = relations.filter(other => other.id !== rel.id);
              const others = relations;

              let lastNode = rel.target[1].id;
              const visitedNodes = [rel.target[0].id, lastNode];

              let noCycles = true;
              while (noCycles) {
                  let other = others.find(other => lastNode === other.target[0].id);
                  if (other) {
                      lastNode = other.target[1].id;
                      if (visitedNodes.includes(lastNode)) {
                          noCycles = false;
                      } else {
                          visitedNodes.push(lastNode);
                      }
                  } else {
                      break;
                  }
              }

              if (!noCycles) {
                  window.alert(`Component cannot be connected to itself or form cyclic relations with other components.`);
              }

              return noCycles;
          }

function initRecogito() {
  const recogito = Recogito.init({
    content: 'content', // Element id or DOM node to attach to
    locale: 'auto',
    allowEmpty: true,
    widgets: [
      { widget: 'TAG', vocabulary: componentLabels }
    ],
    relationVocabulary: relationLabels,
    formatter: formatAnn
  });

  recogito.on('selectAnnotation', function(a) {
    console.log('selected', a);
  });

  recogito.on('createAnnotation', function(ann) {
    if (ann.motivation === 'linking') {
      if (!isRelationValid(ann, recogito)) {
        recogito.removeRelation(ann);
      } else {
        toggleModeBtn.click();
      }
    } else {
      if (!isComponentValid(ann, recogito)) {
        recogito.removeAnnotation(ann);
      } else {
        if (getLabels(ann)[0] === premise) {
          toggleModeBtn.click();
        }
      }
    }
  });

  recogito.on('updateAnnotation', function(curAnn, prevAnn) {
    if (curAnn.motivation === 'linking') {
      if (!isRelationValid(curAnn, recogito)) {
        recogito.removeRelation(curAnn);
      }
    } else {
      if (!isComponentValid(curAnn, recogito)) {
        recogito.removeAnnotation(curAnn);
        recogito.addAnnotation(prevAnn);
      } else {
        propagateComponentUpdate(prevAnn, curAnn, recogito);
      }
    }
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

   $("#submit-sam").click(function () {
      if (validatePremises(recogito)) {
        currentview = new Questionnaire();
      }
  });
}

const StroopExperiment = function () {
  // Load the stage.html snippet into the body of the page
  psiTurk.showPage('stage.html');

  initRecogito();
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
