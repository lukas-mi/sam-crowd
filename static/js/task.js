/*
 * Requires:
 *     psiturk.js
 *     utils.js
 */

// Initialize psiturk object
const psiTurk = new PsiTurk(uniqueId, adServerLoc, mode);

var mycondition = condition;  // these two variables are passed by the psiturk server process
var mycounterbalance = counterbalance;  // they tell you which condition you have been assigned to
// they are not used in the stroop code but may be useful to you

// All pages to be loaded
const pages = [
	"stage.html",
	"questionnaire.html"
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
let annotationMode;
let hitData;
const init = (async () => {
  await psiTurk.preloadPages(pages);

  const hitId = (new URL(document.location)).searchParams.get('hitId');
  const hitInfoURL = `hit_info/${hitId}`;

  await $.get(hitInfoURL).done(data => {
    hitData = data;
    annotationMode = hitData.annotation_mode;
  }).catch((jqXHR, textStatus, errorThrown) => {
    console.log(`got error on ${hitInfoURL}`, jqXHR, textStatus, errorThrown)
  });
})();

/********************
* HTML manipulation
*
* All HTML files in the templates directory are requested
* from the server when the PsiTurk object is created above. We
* need code to get those pages from the PsiTurk object and
* insert them into the document.
*
********************/

/**********************************************
* Structured Argument Mining (SAM) Experiment *
**********************************************/
const fullMode = 'full';
const articleMode = 'article';
const sectionMode = 'section';

const majorClaim = 'MajorClaim';
const claimFor = 'ClaimFor';
const claimAgainst = 'ClaimAgainst';
const premise = 'Premise';
const fullComponentLabels = [majorClaim, claimFor, claimAgainst, premise];
const articleComponentLabels = [majorClaim];
const sectionComponentLabels = [claimFor, claimAgainst, premise];

const support = 'Support';
const attack = 'Attack';
const relationLabels = [support, attack];

const labelsToCSS = {}
labelsToCSS[majorClaim] = 'major-claim';
labelsToCSS[claimFor] = 'claim-for';
labelsToCSS[claimAgainst] = 'claim-against';
labelsToCSS[premise] = 'premise';

function getAnnModeComponentLabels() {
  if (annotationMode === articleMode) {
    return articleComponentLabels;
  } else if (annotationMode === sectionMode) {
    return sectionComponentLabels;
  } else {
    return fullComponentLabels;
  }
}

function getAnnModeRelationLabels() {
  if (annotationMode === articleMode) {
    return [];
  } else {
    return relationLabels;
  }
}

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
  const validLabels = getAnnModeComponentLabels();

  let isValid = false
  if (labels.length === 0) {
    window.alert(`A tag must be added for the highlighted text area.`);
  } else if (labels.length > 1) {
    window.alert(`Only one tag is allowed per highlighted text area.`);
  } else if (!validLabels.includes(labels[0])) {
    window.alert(`Tag '${labels[0]}' is invalid, please add one the following: ${validLabels.join(', ')}.`);
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
      const noOverlap = otherEnd <= compStart || otherStart >= compEnd;
      result = !noOverlap;
    }

    return result;
  });

  let isValid = true;
  if (overlapping.length > 0) {
    isValid = false;
    window.alert('Highlighted text areas must not overlap.');
  }

  return isValid;
}

function isComponentDeletionValid(comp) {
  let isValid = true;
  if (annotationMode === sectionMode && getLabels(comp)[0] === majorClaim) {
    window.alert(`Cannot delete pre-annotated components of type ${majorClaim}.`);
    isValid = false;
  }
  return isValid;
}

function propagateComponentUpdate(prevComp, curComp, recogito) {
  const relations = recogito.getRelationsOnly();
  const prevLabel = getLabels(prevComp)[0];
  const curLabel = getLabels(curComp)[0];

  let relationsToRemove = [];
  let errMsg = '';

  if (prevLabel === premise && (curLabel === claimFor || curLabel === claimAgainst)) { // premise to regular claim => remove outgoing connection
    const outRelation = relations.find(rel => rel.target[0].id === curComp.id);
    relationsToRemove = outRelation ? [outRelation] : [];
    errMsg = `Outgoing connection was removed for the component due to tag change: ${prevLabel} -> ${curLabel}.`;
  } else if (prevLabel === premise && curLabel === majorClaim) { // premise to major claim => remove all connections
    relationsToRemove = relations.filter(rel => rel.target[0].id === curComp.id || rel.target[1].id === curComp.id);
    if (relationsToRemove)
    errMsg = `All connection were removed for the component due to tag change: ${prevLabel} -> ${curLabel}.`;
  } else if ((prevLabel === claimFor || prevLabel === claimAgainst) && curLabel === majorClaim) { // regular claim to major claim => remove all incoming connections
    relationsToRemove = relations.filter(rel => rel.target[1].id === curComp.id);
    errMsg = `All incoming connection were removed for the component due to tag change: ${prevLabel} -> ${curLabel}.`;
  }

  relationsToRemove.forEach(rel => recogito.removeRelation(rel));
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
    suggestionList.append(`<li>Link a ${premise} to ${claimFor}/${claimAgainst} component via ${support}/${attack} relation.</li>`);
    suggestionList.append(`<li>Change ${premise} component's tag to ${claimFor}/${claimAgainst}.</li>`);
    suggestionList.append(`<li>Remove ${premise} component.</li>`);

    const itemsP = $(`<p>Following ${premise} components do not adhere to the rule described above:</p>`)
    const itemList = $(`<ul></ul>`);
    unlinkedPremises.forEach(p => {
      const listItem = $(`<li><span class="r6o-annotation premise">${p.target.selector[0].exact}</span></li>`);
      itemList.append(listItem);
    });

    alertDiv.append(generalMsg, $(`<hr>`), errP1, errP2, suggestionList, itemsP, itemList);
    $("#outer-container").append(alertDiv);

    // alert("Cannot submit due to incomplete annotation, please see reasons at the bottom of the page and address them.");
    $("#errors-container").get(0).scrollIntoView({behavior: 'smooth'});
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
  return Recogito.init({
    content: 'content', // Element id or DOM node to attach to
    locale: 'auto',
    allowEmpty: true,
    widgets: [
      { widget: 'TAG', vocabulary: getAnnModeComponentLabels() }
    ],
    relationVocabulary: getAnnModeRelationLabels(),
    formatter: formatAnn
  });
}

// https://stackoverflow.com/a/3410557/4505008
function getIndicesOf(searchStr, str, caseSensitive) {
  const searchStrLen = searchStr.length;
  if (searchStrLen === 0) {
      return [];
  }

  let startIndex = 0, index, indices = [];
  if (!caseSensitive) {
      str = str.toLowerCase();
      searchStr = searchStr.toLowerCase();
  }
  while ((index = str.indexOf(searchStr, startIndex)) > -1) {
      indices.push(index);
      startIndex = index + searchStrLen;
  }
  return indices;
}

function createAnnotation(text, start, end, label) {
  return {
    '@context': 'http://www.w3.org/ns/anno.jsonld',
    'id': `#mc-${start}-${end}-${Date.now()}`,
    'type': 'Annotation',
    'body': [{
      'type': 'TextualBody',
      'purpose': 'tagging',
      'value': label
    }],
    'target': {
      'selector': [{
        'type': 'TextQuoteSelector',
        'exact': text
      }, {
        'type': 'TextPositionSelector',
        'start': start + 1,
        'end': end + 1
      }]
    }
  };
}

function prepareContent() {
  const contentLines = hitData.content.split('\n');

  const metaDiv = $('#meta');
  metaDiv.append(`<p>The article title: "<strong>${contentLines[0]}</strong>"</p>`)

  const labelSpans = getAnnModeComponentLabels().map(label => `<span class="${labelsToCSS[label]}"><strong>${label}</strong></span>`)

  if (annotationMode === sectionMode) {
    metaDiv.append(`<p>Major claim occurrences:</p>`);
    const ul = $(`<ul>`);
    hitData.meta.major_claim.occurrences.forEach(val => ul.append(`<li><span class="major-claim">${val}</span></li>`));
    metaDiv.append(ul);
    metaDiv.append(`<p>Your task is to annotate components (${labelSpans}) and relations (<strong>${relationLabels.join('/')}</strong>) in the text below.</p>`);
  } else if (annotationMode === articleMode) {
    metaDiv.append(`<p>Your task is to annotate ${labelSpans} occurances in the text below.</p>`);
  } else {
    metaDiv.append(`<p>Your task is to annotate components (${labelSpans}) and relations (<strong>${relationLabels.join('/')}</strong>) in the text below.</p>`);
  }

  metaDiv.append(`<p>Before starting the work read the instructions carefully (click <strong>Open Guidelines</strong> to open guidelines in a new window). You might have done similar task previously, however, this task may be <strong>different</strong> or/and instructions may have been updated.</p>`)

  const contentDiv = $('#content');

  // Skip 2 lines: title and an empty line
  for (let i = 2; i < contentLines.length; i++) {
    // Whitespace at the beginning of every line is necessary,
    // otherwise, cross-line relation arrows will break when components start at the beginning of a line.
    contentDiv.append(`<p> ${contentLines[i]}</p>`);
  }
}

function preAnnotate(recogito) {
  if (annotationMode === sectionMode) {
    hitData.meta.major_claim.occurrences.forEach(mc => {
      const mcLength = mc.length;
      getIndicesOf(mc, hitData.content, true).forEach(start => {
        const newAnn = createAnnotation(mc, start, start + mcLength, majorClaim);
        recogito.addAnnotation(newAnn);
      });
    });
  }
}

function logMetadata() {
  psiTurk.recordTrialData({
    'phase':'survey',
    'event': 'log_metadata',
    'annotation_mode': annotationMode,
    'publisher': hitData.publisher,
    'article': hitData.article,
    'excerpt': hitData.excerpt,
    'major_claim': hitData.meta.major_claim
  });
  psiTurk.saveData({});
}

const SAMExperiment = function () {
  psiTurk.startTask();
  logMetadata();

  psiTurk.showPage('stage.html');
  prepareContent();

  console.log(`annotationMode=${annotationMode}`);

  const r = initRecogito();
  preAnnotate(r);

  let modeToggle;
  if (annotationMode === sectionMode || annotationMode === fullMode) {
    // https://gitbrent.github.io/bootstrap4-toggle
    modeToggle = $(`<input id="mode-toggle" type="checkbox" checked data-toggle="toggle" data-on="<i class='fa fa-play'></i>" data-off="<i class='fa fa-pause'></i>" data-onstyle="dark" data-offstyle="light">`);
    $('#top-navbar-row').append(modeToggle);

    modeToggle.bootstrapToggle({
      on: 'Components',
      off: 'Relations'
    });

    modeToggle.change(function() {
      if($(this).is(':checked')){
        r.setMode('ANNOTATION');
      } else {
        r.setMode('RELATIONS');
      }
    });
  }

  r.on('createAnnotation', function(ann) {
    let ann_type = ann.motivation ? ann.motivation : 'highlighting';
    let isValid;

    if (ann_type === 'linking') {
      isValid = isRelationValid(ann, r);
      if (!isValid) {
        r.removeRelation(ann);
      } else {
        modeToggle.bootstrapToggle('toggle');
      }
    } else {
      isValid = isComponentValid(ann, r);
      if (!isValid) {
        r.removeAnnotation(ann);
      } else {
        if (getLabels(ann)[0] === premise) {
          modeToggle.bootstrapToggle('toggle');
        }
      }
    }

    // TODO: when invalid, log reason
    psiTurk.recordTrialData({
      'phase':'survey',
      'event': 'create_annotation',
      'valid': isValid,
      'annotation': ann,
      'type': ann_type
    });
    psiTurk.saveData({});
  });

  r.on('deleteAnnotation', function(ann) {
    let ann_type = ann.motivation ? ann.motivation : 'highlighting';
    let isValid = true;

    if (ann_type === 'highlighting') {
      isValid = isComponentDeletionValid(ann);
      if (!isValid) {
        r.addAnnotation(ann);
      }
    }

    // TODO: when invalid, log reason
    psiTurk.recordTrialData({
        'phase':'survey',
        'event': 'delete_annotation',
        'valid': isValid,
        'annotation': ann,
        'type': ann_type
      });
      psiTurk.saveData({});
  });

  r.on('updateAnnotation', function(curAnn, prevAnn) {
    let ann_type = curAnn.motivation ? curAnn.motivation : 'highlighting';
    let isValid;

    if (ann_type === 'linking') {
      isValid = isRelationValid(curAnn, r);
      if (!isValid) {
        r.removeRelation(curAnn);
      } else {
        modeToggle.bootstrapToggle('toggle');
      }
    } else {
      isValid = isComponentValid(curAnn, r);
      if (!isValid) {
        r.removeAnnotation(curAnn);
        r.addAnnotation(prevAnn);
      } else {
        propagateComponentUpdate(prevAnn, curAnn, r);
        if (getLabels(curAnn)[0] === premise) {
          modeToggle.bootstrapToggle('toggle');
        }
      }
    }

    // TODO: when invalid, log reason
    psiTurk.recordTrialData({
      'phase':'survey',
      'event': 'update_annotation',
      'valid': isValid,
      'cur_annotation': curAnn,
      'prev_annotation': prevAnn,
      'type': ann_type
    });
    psiTurk.saveData({});
  });

  const getAnnBtn = $('#log-annotations')
  if (mode === 'debug') {
    getAnnBtn.removeAttr('hidden');
    getAnnBtn.click(function () {
      console.log('annotations', r.getAnnotations());
    });
  }

  $('#open-guidelines').click(function () {
    psiTurk.recordTrialData({
      'phase':'survey',
      'event': 'open_guidelines'
    });
    psiTurk.saveData({});
    window.open(
      `guidelines/${annotationMode}`,
      'Guidelines',
      'Popup',
      'toolbar=no,location=no,status=no,menubar=no,scrollbars=yes,resizable=no,width='+1024+',height='+768+''
    )
  });

  $("#submit-sam").click(function () {
    if (validatePremises(r)) {
      psiTurk.recordTrialData({
        'phase':'survey',
        'event': 'submit_annotations',
        'components': r.getAnnotationsOnly(),
        'relations': r.getRelationsOnly()
      });
      psiTurk.saveData({});
      currentView = new Questionnaire();
    } else {
      psiTurk.recordTrialData({
        'phase':'survey',
        'event': 'premise_validation_failure'
      });
      psiTurk.saveData({});
    }
  });
};

/****************
* Questionnaire *
****************/

const Questionnaire = function() {
  const resubmitDiv = $(`<div class="container"></div>`);
  const alertDiv = $(`<div class="alert alert-danger" role="alert">`);
  alertDiv.append(`<h1>Failed to resubmit</h1>`);
  alertDiv.append(`<p>Something went wrong submitting your HIT. This might happen if you lose your internet connection. Press the button to resubmit.</p>`);
  resubmitDiv.append(alertDiv);
  resubmitDiv.append(`<button id="resubmit" class="btn btn-primary btn-lg">Resubmit</button>`);

  const resubmittingDiv = $(`<div class="alert alert-secondary" role="alert"><h1>Trying to resubmit...</h1></div>`)

	function recordResponses() {
    psiTurk.recordTrialData({'phase':'questionnaire', 'status':'submit'});
    $('textarea').each((idx, elem) => psiTurk.recordUnstructuredData(elem.id, elem.value));
    $('select').each((idx, elem) => psiTurk.recordUnstructuredData(elem.id, elem.value));
	}

	function promptResubmit() {
    $('body').html(resubmitDiv);
    $("#resubmit").click(resubmit);
	}

	function resubmit() {
    $('body').html(resubmittingDiv);
    const rePrompt = setTimeout(promptResubmit, 10000);

		psiTurk.saveData({
			success: () => {
			    clearInterval(rePrompt);
          psiTurk.completeHIT();
			},
			error: promptResubmit
		});
	}

	// Load the questionnaire snippet
	psiTurk.showPage('questionnaire.html');
	psiTurk.recordTrialData({'phase':'questionnaire', 'status':'begin'});

	$("#continue").click(() => {
	    recordResponses();
	    psiTurk.saveData({
        success: psiTurk.completeHIT,
        error: promptResubmit
      });
	});


};

// Task object to keep track of the current phase
let currentView;

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
  currentView = new SAMExperiment();
});
